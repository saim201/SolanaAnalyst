FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt --no-cache-dir

# Copy application code
COPY app ${LAMBDA_TASK_ROOT}/app
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set proper permissions
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

# Set the Lambda handler
CMD ["lambda_handler.lambda_handler"]   