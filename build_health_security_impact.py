import json
from pathlib import Path

from build_inmigration_scenario import FastWorkbook, numeric


ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "PPED-AreaSexoEdadNac-2018-2070_mod.xlsx"
OUT = ROOT / "outputs"

SMLMV_2026 = 1_750_905
HEALTH_CONTRIBUTION_RATE = 0.125
FORMALITY_RATE = 0.447
EFFECTIVE_CONTRIBUTION_RATE = FORMALITY_RATE

# UPC-C 2026, annual value, normal zone, by age/sex group.
# Source: Resolucion 2764 de 2025, Ministerio de Salud y Proteccion Social.
UPC_C_2026 = {
    "under_1": 4_971_095.72,
    "age_1_4": 1_429_650.37,
    "age_5_14": 576_471.92,
    "age_15_18_men": 556_399.09,
    "age_15_18_women": 872_919.50,
    "age_19_44_men": 959_680.60,
    "age_19_44_women": 1_772_215.70,
    "age_45_49": 1_808_545.87,
    "age_50_54": 2_288_635.00,
    "age_55_59": 2_709_335.09,
    "age_60_64": 3_478_904.37,
    "age_65_69": 4_309_355.72,
    "age_70_74": 5_210_808.50,
    "age_75_plus": 6_500_944.37,
}


def indicator_rows(years, pop, participation_h, participation_m):
    rows = []
    for year in years:
        p = pop[year]
        men = sum(p[:101])
        women = sum(p[101:])
        age_0_14 = sum(p[0:15]) + sum(p[101:116])
        age_15_64 = sum(p[15:65]) + sum(p[116:166])
        age_65_plus = sum(p[65:101]) + sum(p[166:202])
        pet = age_15_64 + age_65_plus
        labor_h = None
        labor_m = None
        pea = None
        if year in participation_h:
            labor_h = sum(p[15 + i] * participation_h[year][i] for i in range(71))
            labor_m = sum(p[116 + i] * participation_m[year][i] for i in range(71))
            pea = labor_h + labor_m
        rows.append(
            {
                "year": year,
                "total": men + women,
                "pet": pet,
                "pea": pea,
                "labor_h": labor_h,
                "labor_m": labor_m,
            }
        )
    return rows


def build_demographic_populations():
    wb = FastWorkbook(XLSX)
    years = [int(wb.cell("Poblacion Base", row, 1)) for row in range(2, 55)]

    base = {
        year: [numeric(wb.cell("Poblacion Base", row, col)) for col in range(2, 204)]
        for row, year in enumerate(years, start=2)
    }
    alt_emig = {
        year: [numeric(wb.cell("Poblacion Alt", row, col)) for col in range(2, 204)]
        for row, year in enumerate(years, start=2)
    }

    base_migration = {
        int(wb.cell("Serie_Migracion", row, 1)): numeric(wb.cell("Serie_Migracion", row, 2))
        for row in range(2, 55)
    }
    emigration_migration = {
        int(wb.cell("Serie_Migracion", row, 1)): numeric(wb.cell("Serie_Migracion", row, 3))
        for row in range(2, 55)
    }
    constant_inmigration = sum(base_migration[y] for y in range(2020, 2026)) / 6.0
    migration_inmig = {
        year: base_migration[year] if year <= 2027 else constant_inmigration for year in years
    }

    men_weight = 373164 / (373164 + 318057)
    women_weight = 318057 / (373164 + 318057)
    survival = {
        year: [
            numeric(wb.cell("SupxSexoEdad", year + 10 - 2018, col))
            for col in range(8, 210)
        ]
        for year in years
    }

    def build_alternative(migration_alt):
        diff_total = {year: migration_alt[year] - base_migration[year] for year in years}
        diff_by_col = {}
        for year in years:
            source_row = (year - 2018) + 4
            row_diff = []
            for col_index in range(202):
                if col_index < 101:
                    proportion = numeric(wb.cell("Serie_por_edad", source_row, 13 + col_index))
                    row_diff.append(diff_total[year] * men_weight * proportion)
                else:
                    proportion = numeric(wb.cell("Serie_por_edad", source_row, 114 + (col_index - 101)))
                    row_diff.append(diff_total[year] * women_weight * proportion)
            diff_by_col[year] = row_diff

        alternative = {}
        for year in years:
            row = []
            previous_year = year - 1
            for col_index in range(202):
                if year <= 2027:
                    row.append(base[year][col_index])
                elif col_index in (0, 101):
                    row.append(base[year][col_index] + diff_by_col[year][col_index])
                else:
                    carry = survival[year][col_index - 1] * (
                        alternative[previous_year][col_index - 1]
                        - base[previous_year][col_index - 1]
                    )
                    row.append(base[year][col_index] + carry + diff_by_col[year][col_index])
            alternative[year] = row
        return alternative

    alt_inmig = build_alternative(migration_inmig)
    alt_emig_rebuilt = build_alternative(emigration_migration)
    max_rebuild_error = max(
        abs(alt_emig_rebuilt[year][col] - alt_emig[year][col])
        for year in years
        for col in range(202)
    )

    participation_h = {
        int(wb.cell("Matriz_hombres", row, 1)): [
            numeric(wb.cell("Matriz_hombres", row, col)) for col in range(2, 73)
        ]
        for row in range(2, 50)
    }
    participation_m = {
        int(wb.cell("Matriz_mujeres", row, 1)): [
            numeric(wb.cell("Matriz_mujeres", row, col)) for col in range(2, 73)
        ]
        for row in range(2, 50)
    }

    populations = {
        "base": base,
        "emigration_constant": alt_emig,
        "inmigration_constant": alt_inmig,
    }
    indicators = {
        scenario: indicator_rows(years, pop, participation_h, participation_m)
        for scenario, pop in populations.items()
    }
    return years, populations, indicators, max_rebuild_error


def upc_for_age_sex(age, sex):
    if age == 0:
        return UPC_C_2026["under_1"]
    if age <= 4:
        return UPC_C_2026["age_1_4"]
    if age <= 14:
        return UPC_C_2026["age_5_14"]
    if age <= 18:
        return UPC_C_2026["age_15_18_men" if sex == "men" else "age_15_18_women"]
    if age <= 44:
        return UPC_C_2026["age_19_44_men" if sex == "men" else "age_19_44_women"]
    if age <= 49:
        return UPC_C_2026["age_45_49"]
    if age <= 54:
        return UPC_C_2026["age_50_54"]
    if age <= 59:
        return UPC_C_2026["age_55_59"]
    if age <= 64:
        return UPC_C_2026["age_60_64"]
    if age <= 69:
        return UPC_C_2026["age_65_69"]
    if age <= 74:
        return UPC_C_2026["age_70_74"]
    return UPC_C_2026["age_75_plus"]


def upc_cost(population_row):
    cost = 0.0
    for age in range(101):
        cost += population_row[age] * upc_for_age_sex(age, "men")
    for age in range(101):
        cost += population_row[101 + age] * upc_for_age_sex(age, "women")
    return cost


def main():
    years, populations, indicators, max_rebuild_error = build_demographic_populations()
    annual_contribution_per_worker = SMLMV_2026 * 12 * HEALTH_CONTRIBUTION_RATE

    result = {
        "assumptions": {
            "smlmv_2026": SMLMV_2026,
            "health_contribution_rate": HEALTH_CONTRIBUTION_RATE,
            "annual_contribution_per_worker": annual_contribution_per_worker,
            "formality_rate": FORMALITY_RATE,
            "effective_contribution_rate": EFFECTIVE_CONTRIBUTION_RATE,
            "upc_regime": "UPC-C 2026, zona normal",
            "upc_c_2026": UPC_C_2026,
            "max_emigration_rebuild_error": max_rebuild_error,
        },
        "scenarios": {},
    }

    for scenario, pop in populations.items():
        indicator_by_year = {row["year"]: row for row in indicators[scenario]}
        rows = []
        for year in years:
            pea = indicator_by_year[year]["pea"]
            if pea is None:
                continue
            cost = upc_cost(pop[year])
            contributors = pea * EFFECTIVE_CONTRIBUTION_RATE
            revenue = contributors * annual_contribution_per_worker
            balance = revenue - cost
            rows.append(
                {
                    "year": year,
                    "population_total": indicator_by_year[year]["total"],
                    "pea": pea,
                    "upc_cost": cost,
                    "contributors": contributors,
                    "revenue": revenue,
                    "balance": balance,
                    "balance_ratio": balance / cost,
                }
            )
        result["scenarios"][scenario] = rows

    OUT.mkdir(exist_ok=True)
    output_path = OUT / "health_security_impact_results.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(json.dumps(result["assumptions"], ensure_ascii=False, indent=2))
    for scenario, rows in result["scenarios"].items():
        indexed = {row["year"]: row for row in rows}
        print(scenario)
        for year in [2028, 2034, 2050, 2070]:
            row = indexed[year]
            print(
                year,
                round(row["revenue"] / 1e12, 2),
                round(row["upc_cost"] / 1e12, 2),
                round(row["balance"] / 1e12, 2),
                round(row["balance_ratio"], 3),
            )


if __name__ == "__main__":
    main()
