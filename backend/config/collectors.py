"""Lead collector source filters and outreach policy."""

GOV_SOURCES: tuple[str, ...] = (
    "fssp",
    "kad_arbitr",
    "efrsb",
    "fns",
    "rosreestr",
)

SOURCE_PRIORITY: dict[str, int] = {
    "kad_arbitr": 1,
    "efrsb": 2,
    "fssp": 3,
    "fns": 4,
    "rosreestr": 5,
}

FSSP_FILTERS: dict[str, object] = {
    "min_total_debt": 500_000_00,  # kopecks
    "min_proceedings": 2,
    "regions": ["77", "50"],  # Moscow, Moscow oblast
    "exclude_types": ["алименты", "штраф гибдд"],
}

KAD_FILTERS: dict[str, object] = {
    "statuses": ["left_without_progress", "returned", "no_representative"],
    "regions": ["MSK", "MO", "SPB"],
}

EFRSB_FILTERS: dict[str, object] = {
    "message_types": [
        "bankruptcy_petition_filed",
        "restructuring_introduced",
        "asset_sale_introduced",
    ],
    "regions": ["77", "50", "78"],
    "no_representative": True,
}

FNS_FILTERS: dict[str, object] = {
    "status": "ceased",
    "regions": ["77", "50"],
}

ROSREESTR_FILTERS: dict[str, object] = {
    "encumbrance_type": ["arrest", "prohibition"],
    "property_type": ["residential"],
    "regions": ["77", "50"],
}

OUTREACH_MAX_ATTEMPTS: int = 3
OUTREACH_WAIT_DAYS: int = 7

OUTREACH_TEMPLATE: str = (
    "{name}, здравствуйте. Мы специализируемся на помощи с задолженностями. "
    "По открытым данным, у вас может быть ситуация, в которой мы можем помочь. "
    "Если актуально, ответьте, и мы бесплатно оценим ваши варианты. "
    "НССБ «Максимум», bankrotstvo.ai"
)

