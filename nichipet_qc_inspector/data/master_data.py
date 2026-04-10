NICHIPET_MODELS = [
    {
        "model_code": "00-NPX2-2",
        "display_name": "Nichipet EX II 2 μL",
        "volume_range_ul": [0.1, 2.0],
        "test_points": [
            {"selected_volume_ul": 0.2, "ac_limit_percent": 12.0, "cv_limit_percent": 6.0},
            {"selected_volume_ul": 1.0, "ac_limit_percent": 5.0, "cv_limit_percent": 2.5},
            {"selected_volume_ul": 2.0, "ac_limit_percent": 3.0, "cv_limit_percent": 1.0},
        ],
        "notes": ["Below 0.2 μL, AC and CV depend on skill and sampling condition."],
    },
    {
        "model_code": "00-NPX2-10",
        "display_name": "Nichipet EX II 10 μL",
        "volume_range_ul": [0.5, 10.0],
        "test_points": [
            {"selected_volume_ul": 1.0, "ac_limit_percent": 4.0, "cv_limit_percent": 3.0},
            {"selected_volume_ul": 5.0, "ac_limit_percent": 1.0, "cv_limit_percent": 1.0},
            {"selected_volume_ul": 10.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.5},
        ],
        "notes": ["Below 1 μL, AC and CV depend on skill and sampling condition."],
    },
    {
        "model_code": "00-NPX2-20",
        "display_name": "Nichipet EX II 20 μL",
        "volume_range_ul": [2.0, 20.0],
        "test_points": [
            {"selected_volume_ul": 2.0, "ac_limit_percent": 5.0, "cv_limit_percent": 3.0},
            {"selected_volume_ul": 10.0, "ac_limit_percent": 1.0, "cv_limit_percent": 1.0},
            {"selected_volume_ul": 20.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.4},
        ],
        "notes": [],
    },
    {
        "model_code": "00-NPX2-100",
        "display_name": "Nichipet EX II 100 μL",
        "volume_range_ul": [10.0, 100.0],
        "test_points": [
            {"selected_volume_ul": 10.0, "ac_limit_percent": 2.0, "cv_limit_percent": 1.0},
            {"selected_volume_ul": 50.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 100.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.3},
        ],
        "notes": [],
    },
    {
        "model_code": "00-NPX2-200",
        "display_name": "Nichipet EX II 200 μL",
        "volume_range_ul": [20.0, 200.0],
        "test_points": [
            {"selected_volume_ul": 20.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.5},
            {"selected_volume_ul": 100.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 200.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.2},
        ],
        "notes": [],
    },
    {
        "model_code": "00-NPX2-1000",
        "display_name": "Nichipet EX II 1000 μL",
        "volume_range_ul": [100.0, 1000.0],
        "test_points": [
            {"selected_volume_ul": 100.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.5},
            {"selected_volume_ul": 500.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 1000.0, "ac_limit_percent": 0.7, "cv_limit_percent": 0.2},
        ],
        "notes": [],
    },
    {
        "model_code": "00-NPX2-5000",
        "display_name": "Nichipet EX II 5000 μL",
        "volume_range_ul": [1000.0, 5000.0],
        "test_points": [
            {"selected_volume_ul": 1000.0, "ac_limit_percent": 1.0, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 2500.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 5000.0, "ac_limit_percent": 0.6, "cv_limit_percent": 0.2},
        ],
        "notes": [],
    },
    {
        "model_code": "00-NPX2-10000",
        "display_name": "Nichipet EX II 10000 μL",
        "volume_range_ul": [1000.0, 10000.0],
        "test_points": [
            {"selected_volume_ul": 1000.0, "ac_limit_percent": 2.0, "cv_limit_percent": 0.4},
            {"selected_volume_ul": 5000.0, "ac_limit_percent": 0.8, "cv_limit_percent": 0.3},
            {"selected_volume_ul": 10000.0, "ac_limit_percent": 0.4, "cv_limit_percent": 0.2},
        ],
        "notes": [],
    },
]

HELP_NOTES = [
    "Use forward pipetting technique.",
    "Use Premium Tip.",
    "Pre-rinse tip 2–3 times when strict precision is required.",
    "Small volumes under 50 μL are sensitive to evaporation and handling.",
]

TROUBLESHOOTING_GUIDANCE = {
    "tip cannot be ejected": [
        "Nozzle cylinder may be loose.",
        "Securely tighten nozzle cylinder.",
    ],
    "fails to aspirate liquid": [
        "Filter may be soaked (1000 / 5000 / 10000 μL).",
        "Replace filter.",
        "Seal ring and O-ring may be reversed.",
        "Reassemble correctly.",
        "Seal ring and/or O-ring may be worn.",
        "Replace seal ring / O-ring set.",
    ],
    "leaks from tip": [
        "Nozzle cylinder may be loose.",
        "Tighten nozzle cylinder.",
        "Nozzle cylinder may be worn.",
        "Replace nozzle cylinder.",
        "Seal ring / O-ring may be worn due to plunger damage or rust.",
        "Replace seal ring / O-ring set.",
        "Tip may be loosely attached.",
        "Reattach firmly or use new tip.",
    ],
    "push button stiff": [
        "Liquid may have entered nozzle cylinder.",
        "Disassemble and clean parts.",
        "Replace corroded parts if needed.",
    ],
}