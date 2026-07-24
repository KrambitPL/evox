# Persistence and job boundary decisions

The persistence lane makes AWS the only production source of truth. `AwsSettings` refuses
to create adapters without all four explicitly named resources and the AWS SDK session must
resolve credentials. This prevents deployment from silently falling back to local state.

Domain documents are stored as Pydantic JSON envelopes in DynamoDB. Document creation is
conditional, making an identifier the idempotency key. Jobs add the current status as a
separate indexed attribute and use DynamoDB conditional updates to claim and complete work,
which prevents two SQS deliveries from running the same job concurrently.

Evidence is stored as JSON in the configured S3 bucket with SSE-KMS and is returned only as
an immutable `s3://` reference scoped to that bucket. SQS FIFO queues use the durable job ID
as `MessageDeduplicationId`; standard queues retain durable job identity and are protected by
the DynamoDB claim transition.

The dispatcher deliberately persists all handler failures as the public `Job.failure`
record. It does not create alternate provider routes, synthetic results, or in-memory
production behavior. The tests contain small AWS client doubles solely to verify contracts.
