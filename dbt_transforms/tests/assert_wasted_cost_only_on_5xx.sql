select * from {{ ref('log_observability_enriched') }}
where (http_status < 500 and wasted_cost_usd <> 0)
   or (http_status >= 500 and wasted_cost_usd = 0 and estimated_cost_usd > 0.000001)
