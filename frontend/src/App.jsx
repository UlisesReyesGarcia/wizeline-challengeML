import { useState } from "react";
import { Authenticator, useAuthenticator } from "@aws-amplify/ui-react";
import { fetchAuthSession } from "aws-amplify/auth";

import {
  createUploadUrl,
  getChampionModel,
  getPredictionResult,
  runBatchPrediction,
  startRetraining,
  uploadCsvToPresignedUrl,
} from "./api/backendClient";

const DEFAULT_TRAINING_DATA_URI =
  "s3://wizeline-challengeml-dev-bucket/training/raw/training_data.csv";

function Dashboard() {
  const { user, signOut } = useAuthenticator((context) => [
    context.user,
    context.signOut,
  ]);

  const [champion, setChampion] = useState(null);
  const [loadingChampion, setLoadingChampion] = useState(false);

  const [predictionFile, setPredictionFile] = useState(null);
  const [uploadingPrediction, setUploadingPrediction] = useState(false);
  const [uploadedPrediction, setUploadedPrediction] = useState(null);

  const [runningPrediction, setRunningPrediction] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);

  const [trainingDataUri, setTrainingDataUri] = useState(DEFAULT_TRAINING_DATA_URI);
  const [runningRetraining, setRunningRetraining] = useState(false);
  const [retrainingResult, setRetrainingResult] = useState(null);

  const [error, setError] = useState("");

  async function showTokenInfo() {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();

    alert(
      idToken
        ? `Sesión activa. ID token length: ${idToken.length}`
        : "No se encontró ID token."
    );
  }

  async function loadChampionModel() {
    try {
      setLoadingChampion(true);
      setError("");

      const data = await getChampionModel();
      setChampion(data);
    } catch (err) {
      setError(err.message || "Error consultando modelo champion.");
    } finally {
      setLoadingChampion(false);
    }
  }

  async function uploadPredictionCsv() {
    try {
      setError("");
      setUploadedPrediction(null);
      setPredictionResult(null);

      if (!predictionFile) {
        throw new Error("Selecciona un archivo CSV de predicción.");
      }

      if (!predictionFile.name.toLowerCase().endsWith(".csv")) {
        throw new Error("El archivo debe ser .csv.");
      }

      setUploadingPrediction(true);

      const uploadMetadata = await createUploadUrl({
        uploadType: "prediction",
        fileName: predictionFile.name,
      });

      await uploadCsvToPresignedUrl({
        uploadUrl: uploadMetadata.upload_url,
        file: predictionFile,
      });

      setUploadedPrediction(uploadMetadata);
    } catch (err) {
      setError(err.message || "Error subiendo CSV de predicción.");
    } finally {
      setUploadingPrediction(false);
    }
  }

  async function executePrediction() {
    try {
      setError("");
      setPredictionResult(null);

      if (!uploadedPrediction?.s3_uri) {
        throw new Error("Primero sube un CSV de predicción.");
      }

      setRunningPrediction(true);

      const prediction = await runBatchPrediction({
        inputS3Uri: uploadedPrediction.s3_uri,
      });

      const result = await getPredictionResult({
        outputS3Uri: prediction.output_s3_uri,
      });

      setPredictionResult({
        ...prediction,
        download_url: result.download_url,
        expires_in_seconds: result.expires_in_seconds,
        content_type: result.content_type,
      });
    } catch (err) {
      setError(
        err.message ||
          "Error ejecutando predicción. Si fue un timeout por cold start, intenta de nuevo."
      );
    } finally {
      setRunningPrediction(false);
    }
  }

  async function executeRetraining() {
    try {
      setError("");
      setRetrainingResult(null);

      if (!trainingDataUri.trim()) {
        throw new Error("Debes indicar un training_data_uri.");
      }

      if (!trainingDataUri.startsWith("s3://")) {
        throw new Error("El training_data_uri debe ser una ruta S3 válida.");
      }

      setRunningRetraining(true);

      const result = await startRetraining({
        trainingDataUri: trainingDataUri.trim(),
      });

      setRetrainingResult(result);
    } catch (err) {
      setError(err.message || "Error disparando reentrenamiento.");
    } finally {
      setRunningRetraining(false);
    }
  }

  const metrics = champion?.metrics?.metrics;
  const metadata = champion?.metadata;
  const retrainingExecution = retrainingResult?.execution;

  return (
    <main className="page">
      <section className="card">
        <h1>wizeline-challengeML</h1>
        <p className="subtitle">Frontend autenticado con Cognito + API Gateway.</p>

        <div className="info-box">
          <strong>Usuario autenticado:</strong>
          <span>{user?.signInDetails?.loginId || user?.username}</span>
        </div>

        <div className="actions">
          <button onClick={showTokenInfo}>Validar sesión</button>
          <button onClick={loadChampionModel} disabled={loadingChampion}>
            {loadingChampion ? "Consultando..." : "Consultar champion"}
          </button>
          <button className="secondary" onClick={signOut}>
            Cerrar sesión
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        {champion && (
          <section className="result-card">
            <h2>Modelo champion actual</h2>

            <div className="grid">
              <div>
                <span className="label">Modelo</span>
                <strong>{champion.metrics?.model_name}</strong>
              </div>

              <div>
                <span className="label">Tipo</span>
                <strong>{champion.metrics?.model_type}</strong>
              </div>

              <div>
                <span className="label">Run ID</span>
                <strong>{champion.metrics?.run_id}</strong>
              </div>

              <div>
                <span className="label">Features</span>
                <strong>{metadata?.feature_count}</strong>
              </div>

              <div>
                <span className="label">RMSE</span>
                <strong>{metrics?.rmse?.toFixed(6)}</strong>
              </div>

              <div>
                <span className="label">MAE</span>
                <strong>{metrics?.mae?.toFixed(6)}</strong>
              </div>

              <div>
                <span className="label">R²</span>
                <strong>{metrics?.r2?.toFixed(6)}</strong>
              </div>

              <div>
                <span className="label">Primary metric</span>
                <strong>{metadata?.primary_metric}</strong>
              </div>
            </div>

            <p className="small">
              Artefacto: <code>{champion.model_uri}</code>
            </p>
          </section>
        )}

        <section className="result-card">
          <h2>Predicción batch</h2>

          <p className="small">
            Sube un CSV con las 20 columnas <code>feature_0</code> a{" "}
            <code>feature_19</code>, luego ejecuta la predicción usando el modelo
            champion.
          </p>

          <div className="upload-box">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                setPredictionFile(event.target.files?.[0] || null);
                setUploadedPrediction(null);
                setPredictionResult(null);
                setError("");
              }}
            />

            <button onClick={uploadPredictionCsv} disabled={uploadingPrediction}>
              {uploadingPrediction ? "Subiendo..." : "Subir CSV"}
            </button>

            <button
              onClick={executePrediction}
              disabled={runningPrediction || !uploadedPrediction}
            >
              {runningPrediction ? "Ejecutando..." : "Ejecutar predicción"}
            </button>
          </div>

          {predictionFile && (
            <p className="small">
              Archivo seleccionado: <strong>{predictionFile.name}</strong>
            </p>
          )}

          {uploadedPrediction && (
            <div className="success-box">
              <strong>CSV subido correctamente.</strong>
              <span>Input S3 URI:</span>
              <code>{uploadedPrediction.s3_uri}</code>
            </div>
          )}

          {predictionResult && (
            <div className="success-box">
              <strong>Predicción completada.</strong>

              <span>Filas calificadas:</span>
              <code>{predictionResult.rows_scored}</code>

              <span>Output S3 URI:</span>
              <code>{predictionResult.output_s3_uri}</code>

              <a
                className="download-link"
                href={predictionResult.download_url}
                target="_blank"
                rel="noreferrer"
              >
                Descargar CSV de predicciones
              </a>
            </div>
          )}
        </section>

        <section className="result-card">
          <h2>Reentrenamiento manual</h2>

          <p className="small">
            Dispara Step Functions usando un CSV histórico en{" "}
            <code>training/raw/</code>. Para esta PoC, el campo viene precargado
            con el dataset base.
          </p>

          <label className="field">
            <span className="label">Training data URI</span>
            <input
              type="text"
              value={trainingDataUri}
              onChange={(event) => {
                setTrainingDataUri(event.target.value);
                setRetrainingResult(null);
                setError("");
              }}
            />
          </label>

          <div className="actions section-actions">
            <button onClick={executeRetraining} disabled={runningRetraining}>
              {runningRetraining ? "Disparando..." : "Disparar reentrenamiento"}
            </button>
          </div>

          {retrainingResult && (
            <div className="success-box">
              <strong>{retrainingResult.message}</strong>

              <span>Training data URI:</span>
              <code>{retrainingExecution?.training_data_uri}</code>

              <span>Execution name:</span>
              <code>{retrainingExecution?.execution_name}</code>

              <span>Execution ARN:</span>
              <code>{retrainingExecution?.execution_arn}</code>

              <span>Start date:</span>
              <code>{retrainingExecution?.start_date}</code>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default function App() {
  return (
    <Authenticator>
      <Dashboard />
    </Authenticator>
  );
}
