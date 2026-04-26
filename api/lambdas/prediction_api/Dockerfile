FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY ml_pipeline/requirements.txt ./ml_pipeline/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r ./ml_pipeline/requirements.txt

COPY ml_pipeline/configs ./ml_pipeline/configs
COPY api/lambdas/prediction_api/handler.py ./handler.py

CMD ["handler.lambda_handler"]
