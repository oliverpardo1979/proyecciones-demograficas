import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "PPED-AreaSexoEdadNac-2018-2070_mod.xlsx"
OUT = ROOT / "outputs"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def col_to_num(col_letters):
    value = 0
    for char in col_letters:
        value = value * 26 + ord(char.upper()) - ord("A") + 1
    return value


def split_cell_ref(ref):
    match = re.match(r"([A-Z]+)([0-9]+)", ref)
    if not match:
        return None, None
    return int(match.group(2)), col_to_num(match.group(1))


class FastWorkbook:
    def __init__(self, path):
        self.path = path
        self.shared_strings = []
        self.sheet_paths = {}
        self.sheet_cache = {}
        self._load_index()

    def _load_index(self):
        with zipfile.ZipFile(self.path) as archive:
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in root.findall("main:si", NS):
                    parts = []
                    for text in item.findall(".//main:t", NS):
                        parts.append(text.text or "")
                    self.shared_strings.append("".join(parts))

            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rel_map = {}
            for rel in rels:
                rel_id = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if rel_id and target:
                    rel_map[rel_id] = "xl/" + target.lstrip("/")

            for sheet in workbook.findall("main:sheets/main:sheet", NS):
                name = sheet.attrib["name"]
                rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
                self.sheet_paths[name] = rel_map[rel_id]

    def sheet(self, name):
        if name not in self.sheet_cache:
            self.sheet_cache[name] = self._parse_sheet(name)
        return self.sheet_cache[name]

    def _parse_sheet(self, name):
        cells = {}
        with zipfile.ZipFile(self.path) as archive:
            root = ET.fromstring(archive.read(self.sheet_paths[name]))

        for cell in root.findall(".//main:sheetData/main:row/main:c", NS):
            ref = cell.attrib.get("r")
            row, col = split_cell_ref(ref)
            if row is None:
                continue

            cell_type = cell.attrib.get("t")
            value_node = cell.find("main:v", NS)
            value = None

            if cell_type == "inlineStr":
                text_node = cell.find(".//main:t", NS)
                value = text_node.text if text_node is not None else None
            elif value_node is not None and value_node.text is not None:
                raw = value_node.text
                if cell_type == "s":
                    value = self.shared_strings[int(raw)]
                elif cell_type == "b":
                    value = raw == "1"
                elif cell_type == "str":
                    value = raw
                else:
                    try:
                        number = float(raw)
                        value = int(number) if number.is_integer() else number
                    except ValueError:
                        value = raw

            cells[(row, col)] = value
        return cells

    def cell(self, sheet_name, row, col):
        return self.sheet(sheet_name).get((row, col))


def numeric(value):
    return 0.0 if value is None else float(value)


def indicator_rows(years, pop, participation_h, participation_m):
    rows = []
    for year in years:
        p = pop[year]
        men = sum(p[:101])
        women = sum(p[101:])
        age_0_14 = sum(p[0:15]) + sum(p[101:116])
        age_15_64 = sum(p[15:65]) + sum(p[116:166])
        age_65_plus = sum(p[65:101]) + sum(p[166:203])
        total = men + women
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
                "total": total,
                "men": men,
                "women": women,
                "age_0_14": age_0_14,
                "age_15_64": age_15_64,
                "age_65_plus": age_65_plus,
                "masculinity": men / women,
                "dep_total": (age_0_14 + age_65_plus) / age_15_64,
                "dep_young": age_0_14 / age_15_64,
                "dep_old": age_65_plus / age_15_64,
                "aging_index": age_65_plus / age_0_14,
                "support_ratio": age_15_64 / age_65_plus,
                "pet": pet,
                "labor_h": labor_h,
                "labor_m": labor_m,
                "pea": pea,
            }
        )
    return rows


def main():
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

    # Same window as the existing narrative, interpreted as a permanent
    # positive inflow for the new immigration scenario.
    constant_inmigration = sum(base_migration[y] for y in range(2020, 2026)) / 6.0

    migration_inmig = {}
    for year in years:
        if year <= 2027:
            migration_inmig[year] = base_migration[year]
        else:
            migration_inmig[year] = constant_inmigration

    men_weight = 373164 / (373164 + 318057)
    women_weight = 318057 / (373164 + 318057)

    survival = {}
    for year in years:
        source_row = year + 10 - 2018
        survival[year] = [numeric(wb.cell("SupxSexoEdad", source_row, col)) for col in range(8, 210)]

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
        return alternative, diff_total

    alt_inmig, inmigr_diff_total = build_alternative(migration_inmig)
    alt_emig_rebuilt, _ = build_alternative(emigration_migration)
    max_emigration_rebuild_error = max(
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

    result = {
        "assumptions": {
            "constant_inmigration_2020_2025_average": constant_inmigration,
            "men_weight": men_weight,
            "women_weight": women_weight,
            "max_emigration_rebuild_error": max_emigration_rebuild_error,
        },
        "migration": [
            {
                "year": year,
                "base": base_migration[year],
                "emigration_constant_balance": emigration_migration[year],
                "inmigration_constant_balance": migration_inmig[year],
                "inmigration_diff": inmigr_diff_total[year],
            }
            for year in years
        ],
        "base": indicator_rows(years, base, participation_h, participation_m),
        "emigration_constant": indicator_rows(years, alt_emig, participation_h, participation_m),
        "inmigration_constant": indicator_rows(years, alt_inmig, participation_h, participation_m),
    }

    OUT.mkdir(exist_ok=True)
    output_path = OUT / "inmigration_scenario_results.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(json.dumps(result["assumptions"], ensure_ascii=False, indent=2))
    for scenario in ["base", "emigration_constant", "inmigration_constant"]:
        indexed = {row["year"]: row for row in result[scenario]}
        print(scenario)
        for year in [2028, 2034, 2050, 2070]:
            row = indexed[year]
            print(
                year,
                round(row["total"]),
                round(row["pet"]),
                None if row["pea"] is None else round(row["pea"]),
                round(row["dep_total"], 4),
                round(row["dep_young"], 4),
                round(row["dep_old"], 4),
                round(row["aging_index"], 4),
            )


if __name__ == "__main__":
    main()
