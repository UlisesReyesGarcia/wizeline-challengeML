# wizeline-challengeML

Producto de datos E2E desplegado en AWS para entrenar modelos de regresión bajo enfoque champion-challenger, promover automáticamente el mejor modelo y exponer predicción batch mediante APIs consumidas por un frontend en React autenticado con Cognito.

## 1. Resumen ejecutivo

La solución implementa cuatro capacidades principales:

1. Carga de datasets históricos en S3 para disparar reentrenamiento.
2. Entrenamiento de varios algoritmos de regresión con `GridSearchCV` en ECS Fargate.
3. Selección y promoción automática del mejor modelo hacia `models/champion/`.
4. Predicción batch sobre archivos CSV usando el modelo champion, operada desde un frontend React.

Consideraciones de infraestructura:

- El frontend usa `AWS Amplify UI/Auth` para autenticacion con Cognito, pero el hosting fue implementado en Terraform es `S3 + CloudFront`.
- DynamoDB se provisiona como base para un model registry, pero la implementación actual consulta el champion desde artefactos JSON en S3; el pipeline no persiste registros operativos en DynamoDB al día de hoy.

## 2. Arquitectura final implementada

```text
Usuario
  |
  v
Frontend React
  |  autenticacion
  +------------------------------> Amazon Cognito
  |
  |  llamadas autenticadas con JWT
  v
Amazon API Gateway HTTP API
  |
  +--> POST /upload-url ------------------> Lambda upload_api
  |                                          |
  |                                          v
  |                                   Presigned URL para S3
  |
  +--> POST /predictions --------------> Lambda prediction_api (contenedor)
  |                                          |
  |                                          +--> lee CSV de inference/input/
  |                                          +--> carga champion model.pkl
  |                                          +--> escribe inference/output/
  |
  +--> GET /model-registry/champion ---> Lambda model_registry_api
  |                                          |
  |                                          +--> lee metadata/metrics desde S3
  |
  +--> POST /retrain ------------------> Lambda training_trigger_api
                                             |
                                             +--> StartExecution Step Functions
                                                        |
                                                        v
                                              Step Functions
                                                        |
                                                        v
                                              ECS Fargate task
                                                        |
                                                        +--> descarga CSV historico
                                                        +--> valida esquema
                                                        +--> entrena challengers
                                                        +--> selecciona mejor modelo
                                                        +--> promueve champion
                                                        +--> sube artefactos a S3

Adicionalmente:
S3 event training/raw/*.csv -> Lambda training_trigger_api -> Step Functions
```

## 3. Componentes del repositorio

```text
wizeline-challengeML/
├── api/
│   └── lambdas/
│       ├── model_registry_api/
│       ├── prediction_api/
│       ├── training_trigger_api/
│       └── upload_api/
├── frontend/
├── infra/
│   └── terraform/
├── ml_pipeline/
│   ├── configs/
│   ├── artifacts/
│   ├── requirements.txt
│   └── src/
├── INFRA_DEF.md
├── PLAN_STEPS.md
└── README.md
```

## 4. Flujo funcional E2E

### 4.1 Reentrenamiento

1. Un CSV histórico se sube a `s3://<bucket>/training/raw/`.
2. S3 dispara `training_trigger_api`.
3. La Lambda inicia una ejecución de Step Functions.
4. Step Functions lanza una tarea de ECS Fargate con variables de entorno que apuntan al dataset, directorio de salida y directorio champion.
5. El contenedor de `ml_pipeline`:
   - descarga el dataset;
   - valida columnas y tipos;
   - separa features y target;
   - entrena varios challengers con grid search;
   - evalua métricas `rmse`, `mae` y `r2`;
   - serializa el mejor challenger a `model.pkl`;
   - compara contra el champion actual;
   - si mejora, copia `model.pkl`, `metrics.json`, `metadata.json` y `promotion_decision.json` a `models/champion/`.

### 4.2 Predicción batch

1. El frontend solicita un presigned URL a `POST /upload-url`.
2. El CSV de inferencia se sube directo a `s3://<bucket>/inference/input/...csv`.
3. El frontend invoca `POST /predictions` con `action=predict`.
4. `prediction_api` descarga el CSV y el champion `model.pkl`.
5. La Lambda valida que el archivo contenga exactamente `feature_0` a `feature_19`.
6. El modelo genera predicciones.
7. El resultado se guarda en `s3://<bucket>/inference/output/..._predictions.csv`.
8. El frontend vuelve a llamar `POST /predictions` con `action=get_result` para obtener un presigned URL de descarga.

### 4.3 Consulta del champion

1. El frontend llama `GET /model-registry/champion`.
2. `model_registry_api` lee en S3:
   - `models/champion/metadata.json`
   - `models/champion/metrics.json`
   - `models/champion/promotion_decision.json`
3. Devuelve información del champion actual y rutas de artefactos.

## 5. Infraestructura AWS provisionada por Terraform

Los recursos viven en `infra/terraform/`.

### 5.1 Básicos

- `providers.tf`: provider AWS con tags comunes.
- `variables.tf`: `project_name`, `environment`, `aws_region`, `aws_profile`.
- `locals.tf`: `name_prefix` y etiquetas compartidas.
- `outputs.tf`: exporta nombres, ARNs y endpoints clave.

### 5.2 Storage

- `aws_s3_bucket.main`: bucket principal del producto.
- Versionado habilitado.
- Bloqueo de acceso público.
- Cifrado SSE-S3 `AES256`.
- Prefijos creados como objetos vacios:
  - `training/raw/`
  - `training/processed/`
  - `training/validation/`
  - `inference/input/`
  - `inference/output/`
  - `models/candidates/`
  - `models/champion/`
  - `models/archived/`
  - `logs/`
- CORS habilitado para desarrollo local y un dominio CloudFront ya definido en el código.

### 5.3 Model Registry Foundation

- `aws_dynamodb_table.model_registry`
  - `PAY_PER_REQUEST`
  - `hash_key = model_id`
  - point-in-time recovery habilitado

Nota importante: hoy la tabla existe a nivel infraestructura, pero la lógica de negocio actual no escribe ni consulta registros desde DynamoDB.

### 5.4 Contenedores y entrenamiento

- `aws_ecr_repository.ml_pipeline`
- `aws_ecr_repository.prediction_api`
- políticas lifecycle para conservar las ultimas 10 imagenes
- `aws_ecs_cluster.ml_pipeline`
- `aws_ecs_task_definition.ml_pipeline`
  - `FARGATE`
  - `cpu = 2048`
  - `memory = 4096`
  - comando: `python ml_pipeline/src/main.py`
- `aws_sfn_state_machine.ml_pipeline`
  - orquesta una sola tarea sincrónica de ECS
- VPC dedicada con:
  - 1 VPC
  - 2 subnets publicas
  - 1 internet gateway
  - 1 route table publica
  - 1 security group para ECS con salida abierta

### 5.5 APIs y seguridad

- `aws_cognito_user_pool.main`
- `aws_cognito_user_pool_client.frontend`
- `aws_apigatewayv2_api.main` tipo HTTP
- `aws_apigatewayv2_authorizer.cognito_jwt`
- stage `$default` con despliegue automatico

Rutas expuestas:

- `POST /upload-url`
- `POST /predictions`
- `GET /model-registry/champion`
- `POST /retrain`

### 5.6 Lambdas

- `upload_api`
  - runtime `python3.12`
  - genera presigned URLs para cargas CSV
- `training_trigger_api`
  - runtime `python3.12`
  - puede ser invocada por API Gateway o por evento S3
- `model_registry_api`
  - runtime `python3.12`
  - lee metadata del champion desde S3
- `prediction_api`
  - Lambda container image
  - ejecuta inferencia batch

### 5.7 Frontend hosting

Terraform crea:

- bucket S3 privado para estáticos del frontend
- CloudFront distribution
- Origin Access Control
- bucket policy para permitir lectura solo desde CloudFront

Esto significa que el frontend final se publica como sitio estatico en `S3 + CloudFront`.

## 6. Pipeline de ML implementado

El pipeline esta en [`ml_pipeline/`](ml_pipeline/).

### 6.1 Validación de datos

El esquema se define en [`ml_pipeline/configs/data_schema.yaml`](ml_pipeline/configs/data_schema.yaml):

- target: `target`
- 20 features numericas:
  - `feature_0` a `feature_19`
- dataset de entrenamiento esperado:
  - 20 features + 1 columna target
- dataset de predicción esperado:
  - solo `feature_0` a `feature_19`

Validaciones implementadas:

- columnas faltantes
- columnas extra
- presencia del target en entrenamiento
- ausencia de valores nulos
- tipos numéricos
- conteo exacto de 20 features

### 6.2 Algoritmos entrenados

Configurados en [`ml_pipeline/configs/model_grids.yaml`](ml_pipeline/configs/model_grids.yaml):

- `LinearRegression`
- `Ridge`
- `Lasso`
- `ElasticNet`
- `RandomForestRegressor`
- `GradientBoostingRegressor`
- `XGBRegressor`

Todos se entrenan con `GridSearchCV`, `cv=5` y métrica de selección `neg_root_mean_squared_error`.

### 6.3 Selección y promoción

- `primary_metric`: `rmse`
- `test_size`: `0.2`
- `random_state`: `42`
- `promotion.min_improvement_pct`: `0.0`

Con esa configuración:

- si no existe champion previo, el challenger ganador se promueve;
- si ya existe champion, cualquier challenger con mejor `rmse` lo reemplaza;
- si no mejora, se conserva el champion actual.

### 6.4 Artefactos generados

Por cada corrida se generan:

- `model.pkl`
- `metrics.json`
- `metadata.json`

Si el modelo es promovido, en `models/champion/` también queda:

- `promotion_decision.json`

## 7. Endpoints y contratos de API

Todos los endpoints requieren JWT de Cognito enviado como `Authorization: Bearer <id_token>`.

### 7.1 `POST /upload-url`

Request:

```json
{
  "upload_type": "prediction",
  "file_name": "batch_input.csv"
}
```

Valores permitidos para `upload_type`:

- `prediction`
- `training`

Response ejemplo:

```json
{
  "bucket": "wizeline-challengeml-dev-bucket",
  "key": "inference/input/20260426_123456_ab12cd34_batch_input.csv",
  "s3_uri": "s3://wizeline-challengeml-dev-bucket/inference/input/20260426_123456_ab12cd34_batch_input.csv",
  "upload_url": "https://...",
  "expires_in_seconds": 900,
  "upload_type": "prediction",
  "content_type": "text/csv"
}
```

### 7.2 `POST /predictions`

Acción para predecir:

```json
{
  "action": "predict",
  "input_s3_uri": "s3://wizeline-challengeml-dev-bucket/inference/input/input.csv"
}
```

Response ejemplo:

```json
{
  "message": "Batch prediction completed successfully",
  "job_id": "prediction_20260426_123456_ab12cd34",
  "input_s3_uri": "s3://...",
  "output_s3_uri": "s3://.../inference/output/prediction_20260426_123456_ab12cd34_predictions.csv",
  "champion_model_uri": "s3://.../models/champion/model.pkl",
  "rows_scored": 100,
  "prediction_column": "prediction"
}
```

Acción para recuperar resultado:

```json
{
  "action": "get_result",
  "output_s3_uri": "s3://wizeline-challengeml-dev-bucket/inference/output/prediction_20260426_123456_ab12cd34_predictions.csv"
}
```

### 7.3 `GET /model-registry/champion`

Devuelve metadata y métricas del champion actual leidas desde S3.

### 7.4 `POST /retrain`

Request:

```json
{
  "training_data_uri": "s3://wizeline-challengeml-dev-bucket/training/raw/training_data.csv"
}
```

Response ejemplo:

```json
{
  "message": "Manual retraining started",
  "execution": {
    "training_data_uri": "s3://...",
    "execution_name": "training-trigger-1714123456-ab12cd34",
    "execution_arn": "arn:aws:states:...",
    "start_date": "2026-04-26T18:30:00.000000"
  }
}
```

## 8. Variables y configuración

### 8.1 Terraform

Variables disponibles en [`infra/terraform/variables.tf`](infra/terraform/variables.tf):

```hcl
project_name = "wizeline-challengeml"
environment  = "dev"
aws_region   = "us-east-1"
aws_profile  = "wizeline-challengeml-dev"
```

Ejemplo recomendado de `terraform.tfvars`:

```hcl
project_name = "wizeline-challengeml"
environment  = "dev"
aws_region   = "us-east-1"
aws_profile  = "wizeline-challengeml-dev"
```

### 8.2 Frontend

Basado en [`frontend/.env.example`](frontend/.env.example):

```bash
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=<user-pool-id>
VITE_COGNITO_USER_POOL_CLIENT_ID=<user-pool-client-id>
VITE_API_ENDPOINT=https://<api-id>.execute-api.us-east-1.amazonaws.com
```

### 8.3 Variables usadas en runtime

#### ECS `ml_pipeline`

- `PROJECT_NAME`
- `ENVIRONMENT`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `MODEL_REGISTRY_TABLE`
- `TRAINING_DATA_URI`
- `OUTPUT_URI`
- `CHAMPION_URI`

#### Lambda `prediction_api`

- `S3_BUCKET_NAME`
- `CHAMPION_MODEL_URI`
- `PREDICTION_OUTPUT_URI`

#### Lambda `model_registry_api`

- `S3_BUCKET_NAME`
- `CHAMPION_PREFIX`

#### Lambda `training_trigger_api`

- `STATE_MACHINE_ARN`
- `S3_BUCKET_NAME`
- `OUTPUT_URI`
- `CHAMPION_URI`

## 9. Prerrequisitos para replicar la solución en AWS

Instala y configura:

- AWS CLI v2
- Terraform `>= 1.6.0`
- Docker
- Node.js y npm
- Python 3.12

También necesitas:

- una cuenta AWS con permisos para S3, Lambda, API Gateway, Cognito, CloudFront, ECS, ECR, Step Functions, IAM y DynamoDB;
- credenciales configuradas en el perfil que uses en Terraform;
- capacidad de construir y publicar imágenes Docker en ECR.

## 10. Despliegue completo en AWS

Por la forma en que está modelada la infraestructura, conviene hacerlo en fases.

### 10.1 Inicializar Terraform

```bash
cd infra/terraform
terraform init
terraform validate
terraform plan
```

### 10.2 Crear primero los repositorios ECR

La Lambda `prediction_api` usa imagen de contenedor, por lo que la imagen debe existir antes del `apply` completo.

```bash
terraform apply \
  -target=aws_ecr_repository.ml_pipeline \
  -target=aws_ecr_lifecycle_policy.ml_pipeline \
  -target=aws_ecr_repository.prediction_api \
  -target=aws_ecr_lifecycle_policy.prediction_api
```

### 10.3 Obtener URLs de ECR

```bash
terraform output ecr_repository_url
terraform output prediction_api_ecr_repository_url
```

### 10.4 Construir y publicar imagen del pipeline ML

Desde la raíz del repo:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

ML_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wizeline-challengeml-dev-ml-pipeline"

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -f ml_pipeline/Dockerfile -t wizeline-ml-pipeline:latest .
docker tag wizeline-ml-pipeline:latest "${ML_REPO}:latest"
docker push "${ML_REPO}:latest"
```

### 10.5 Construir y publicar imagen de `prediction_api`

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

PRED_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/wizeline-challengeml-dev-prediction-api"

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -f api/lambdas/prediction_api/Dockerfile -t wizeline-prediction-api:latest .
docker tag wizeline-prediction-api:latest "${PRED_REPO}:latest"
docker push "${PRED_REPO}:latest"
```

### 10.6 Aplicar la infraestructura completa

```bash
cd infra/terraform
terraform apply
```

### 10.7 Revisar outputs relevantes

```bash
terraform output api_gateway_endpoint
terraform output cognito_user_pool_id
terraform output cognito_user_pool_client_id
terraform output frontend_bucket_name
terraform output frontend_url
terraform output s3_bucket_name
```

## 11. Publicación del frontend

### 11.1 Configurar variables

En `frontend/.env.local`:

```bash
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=<terraform output>
VITE_COGNITO_USER_POOL_CLIENT_ID=<terraform output>
VITE_API_ENDPOINT=<terraform output api_gateway_endpoint>
```

### 11.2 Probar localmente

```bash
cd frontend
npm install
npm run dev
```

### 11.3 Generar build

```bash
npm run build
```

### 11.4 Publicar en el bucket del frontend

```bash
aws s3 sync dist/ s3://<frontend-bucket-name> --delete
```

El sitio quedará disponible en la URL de CloudFront expuesta por `terraform output frontend_url`.

## 12. Cómo usar el frontend actual

La UI actual esta definida principalmente en [`frontend/src/App.jsx`](frontend/src/App.jsx).

### 12.1 Inicio de sesion

- La app usa `Authenticator` de Amplify.
- El login se realiza contra Cognito con email/password.
- Como el user pool permite `allow_admin_create_user_only = false`, el flujo soporta auto-registro.

### 12.2 Consultar el champion

En la pantalla principal:

1. Inicia sesion.
2. Haz clic en `Consultar champion`.
3. La UI mostrara:
   - modelo ganador;
   - tipo de estimador;
   - `run_id`;
   - numero de features;
   - metricas `RMSE`, `MAE`, `R²`;
   - ruta del artefacto champion.

### 12.3 Ejecutar predicción batch

1. Prepara un CSV con exactamente 20 columnas:
   - `feature_0` a `feature_19`
2. Haz clic en `Subir CSV`.
3. La UI solicitará un presigned URL y cargará el archivo a S3.
4. Haz clic en `Ejecutar prediccion`.
5. Al finalizar, se mostrará:
   - `rows_scored`
   - `output_s3_uri`
   - enlace de descarga del CSV con predicciones

### 12.4 Disparar reentrenamiento manual

1. Verifica que el archivo histórico exista en `training/raw/`.
2. En el campo `Training data URI`, captura una ruta valida `s3://.../training/raw/<archivo>.csv`.
3. Haz clic en `Disparar reentrenamiento`.
4. La UI mostrará:
   - `execution_name`
   - `execution_arn`
   - `start_date`

### 12.5 Reentrenamiento automático por carga S3

Si subes un CSV a `training/raw/`, el bucket principal dispara automaticamente la Lambda `training_trigger_api`, sin necesidad de pasar por el frontend.

## 13. Ejecución local del pipeline ML

### 13.1 Con Python local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ml_pipeline/requirements.txt
python ml_pipeline/src/main.py \
  --data-path path/to/training_data.csv \
  --output-dir ml_pipeline/artifacts/candidates \
  --champion-dir ml_pipeline/artifacts/champion
```

### 13.2 Con Docker

```bash
docker build -f ml_pipeline/Dockerfile -t wizeline-ml-pipeline:local .
docker run --rm \
  -v "$(pwd)":/app \
  wizeline-ml-pipeline:local
```

Nota: el pipeline por defecto espera rutas locales o variables de entorno S3; para un flujo real en AWS conviene usarlo a traves de ECS/Step Functions.

## 14. Artefactos esperados en S3

### 14.1 Entrenamiento

```text
training/raw/<archivo>.csv
models/candidates/<run_id>/model.pkl
models/candidates/<run_id>/metrics.json
models/candidates/<run_id>/metadata.json
models/champion/model.pkl
models/champion/metrics.json
models/champion/metadata.json
models/champion/promotion_decision.json
```

### 14.2 Inferencia

```text
inference/input/<archivo>.csv
inference/output/<job_id>_predictions.csv
```

## 15. Observaciones importantes de la implementacion actual

- El archivo [`infra/terraform/main.tf`](infra/terraform/main.tf) está vacío porque los recursos están distribuidos en archivos temáticos.
- La infraestructura del frontend implementada no usa Amplify Hosting; usa CloudFront sobre S3.
- El frontend sí usa `aws-amplify` y `@aws-amplify/ui-react` para autenticación con Cognito.
- DynamoDB está provisionado pero no participa en el flujo operativo actual del champion.
- `POST /retrain` y el trigger S3 reutilizan la misma Lambda.
- La Lambda de predicción opera sobre archivos CSV pequenos o medianos; para cargas muy grandes sería mejor migrar inferencia batch a ECS o un proceso asíncrono adicional.
- No hay pipeline CI/CD en este repositorio al momento de esta documentacion.

## 16. Siguientes mejoras recomendadas

1. Persistir metadata de entrenamiento y estado champion/challenger en DynamoDB para tener un model registry real.
2. Agregar estados intermedios en Step Functions para trazabilidad de validacion, entrenamiento, evaluacion y promocion.
3. Versionar despliegue del frontend y automatizar `build + sync`.
4. Incorporar pruebas automatizadas para Lambdas, pipeline ML y frontend.
5. Endurecer seguridad con dominios permitidos especificos en CORS y control de acceso por grupos Cognito.
6. Agregar monitoreo funcional de ejecuciones, alarmas y dashboards en CloudWatch.
