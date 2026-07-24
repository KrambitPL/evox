# Agent 12 AWS and deployment decisions

Date: 2026-07-24

- Existing environment-owned networking, DNS, certificates, ECR, alarm delivery, and
  Terraform state are inputs. Evox owns its application resources and never creates or
  stores credential values in Terraform.
- Public traffic follows CloudFront to a named HTTPS ALB origin. The ALB security group
  trusts only the AWS-managed CloudFront origin prefix list, and its listener defaults to
  deny unless CloudFront supplies the private rotation-safe origin header.
- API/web tasks and workers use separate security groups and IAM roles. Only workers can
  reach EFS; only API and worker roles can reach application state, evidence, or queues.
- Evidence is private, versioned, encrypted, and TLS-only. DynamoDB uses on-demand
  capacity, encryption, and point-in-time recovery. Queue encryption and a DLQ are
  mandatory.
- Release images are full-SHA, immutable, `linux/amd64`, revision-labelled artifacts.
  Direct deployment reuses an existing image only after checking that label and pins ECS
  to the resolved registry digest.
- Runtime images use current Debian Trixie slim bases. Release vulnerability gates ignore
  findings with no available fix but reject every actionable high or critical finding;
  build-only Python packaging tools are removed from the API runtime image.
- Safe direct deployment treats missing tests, scans, secrets, services, readiness, live
  sponsor verification, or smoke verification as release failures. Clean exact remote
  `main` is reverified after all local gates so generated changes cannot enter an image
  labelled with the prior SHA. A failed first release scales services to zero; a failed
  update restores preceding task definitions.
- The API health route, worker console entrypoint, and built Next.js production output
  remain explicit integration contracts because their implementation belongs to other
  task lanes. No fallback process or synthetic health response is introduced here.
