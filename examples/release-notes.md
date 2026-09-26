# Kestrel Cloud — API v3 release notes

**Released:** 14 August 2026

## Availability

API v3 is generally available in all 12 regions, including the two new ones in Jakarta and São Paulo. Existing v2 keys keep working until 31 January 2027.

## Throughput

The rate limit rises from 100 requests per second to 500 requests per second per project. Burst capacity is 750 requests per second for up to 10 seconds.

## Pricing

Token pricing drops to $0.004 per 1,000 input tokens and $0.016 per 1,000 output tokens. The free tier now includes 10,000 requests per month, up from 2,500. Overage is billed monthly.

## Reliability

The v3 service-level objective is 99.95% monthly uptime, measured at the edge. Latency at p99 was 180 ms during the six-week beta.

## Migrating

The v2 `/v2/generate` endpoint maps to `/v3/responses`. The `max_tokens` parameter is renamed `max_output_tokens`; the old name returns a deprecation warning and is ignored. Streaming behaviour is unchanged.

## Not included

SQL passthrough, on-premise deployment, and a self-hosted gateway were deferred to 2027. SOC 2 Type II certification is still in progress and is not yet complete.
