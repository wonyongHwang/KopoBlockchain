# KopoBlockchain <Team5>

broadcastNewBlock function Update

Number of fails in the nodelst.csv differed from actual number of fails.
This results in requesting once more than the limit(=g_maximumTry).
Therefore, number of fails should count +1 before comparing with limit.