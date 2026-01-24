#!/bin/bash

# Submit Flink Job to the running cluster
# Assumes docker-compose is running

echo "Submitting GraphGuard Fraud Detection Job to Flink..."

docker exec -it graphguard-jobmanager ./bin/flink run \
    -py /opt/graphguard/data-eng/flink/job.py \
    --pyFiles /opt/graphguard/data-eng/flink/fraud_patterns.py

if [ $? -eq 0 ]; then
    echo "Job submitted successfully!"
else
    echo "Job submission failed."
fi
