FROM public.ecr.aws/lambda/python:3.13-arm64

COPY requirements-lambda.txt ${LAMBDA_TASK_ROOT}/requirements-lambda.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-lambda.txt

COPY *.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_handler.handler"]
