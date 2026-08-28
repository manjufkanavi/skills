#!/usr/bin/env python3
"""Regenerate search queries for a specific topic with better focus."""
import json
import sys

topic = sys.argv[1] if len(sys.argv) > 1 else "evolution of mobile phones"

# Generate focused, high-quality search queries for deep research
queries = {
    "round_1": [
        f"evolution of mobile phones history timeline 1G 2G 3G 4G 5G",
        f"mobile phone technology development from 1973 to 2026",
        f"history of cellular networks generations technology",
        f"smartphone evolution iPhone Android market history",
        f"mobile phone hardware evolution processors cameras batteries",
        f"mobile communication standards evolution GSM CDMA LTE 5G NR",
        f"mobile phone market share history Nokia Samsung Apple",
        f"impact of mobile phones on society economy development",
        f"mobile phone usage statistics global adoption rates",
        f"future of mobile phones 6G AI integration trends 2030"
    ],
    "round_2": [
        f"5G technology specifications deployment global coverage 2024 2025 2026",
        f"6G mobile technology research roadmap timeline",
        f"AI on-device processing smartphones neural engines",
        f"foldable smartphone market technology trends",
        f"mobile phone satellite connectivity direct to device",
        f"mobile phone health effects radiation safety studies",
        f"mobile phone digital wellbeing screen time research",
        f"mobile phone environmental impact e-waste sustainability",
        f"mobile phone in developing countries digital divide",
        f"mobile payment systems evolution M-Pesa digital banking"
    ],
    "round_3": [
        f"mobile phone industry revenue market size forecast",
        f"quantum computing impact on mobile communications",
        f"mobile phone AR VR spatial computing integration",
        f"satellite internet mobile phones Starlink direct",
        f"mobile phone biometric security evolution",
        f"mobile phone accessibility features disabilities",
        f"mobile phone privacy data security concerns",
        f"mobile phone chip manufacturing TSMC Samsung foundry",
        f"mobile phone recycling circular economy initiatives",
        f"mobile phone research papers IEEE ACM digital library"
    ]
}

# Save queries for the loop script
with open('skills/deep-research/queries.json', 'w') as f:
    json.dump(queries, f, indent=2)

print(f"Generated {sum(len(v) for v in queries.values())} queries across {len(queries)} rounds")
for round_name, round_queries in queries.items():
    print(f"\n{round_name}:")
    for q in round_queries:
        print(f"  - {q}")
