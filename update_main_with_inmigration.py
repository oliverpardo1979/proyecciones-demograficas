import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "inmigration_scenario_results.json"
MAIN = ROOT / "main.tex"


def tex_int(value):
    return f"{round(value):,}".replace(",", ".")


def coord_value(value, integer=False):
    if integer:
        return str(round(value))
    return f"{value:.9f}".rstrip("0").rstrip(".")


def coordinates(rows, key, integer=False, start_year=None):
    parts = []
    for row in rows:
        if start_year is not None and row["year"] < start_year:
            continue
        value = row.get(key)
        if value is None:
            continue
        parts.append(f"({row['year']},{coord_value(value, integer)})")
    lines = []
    for index in range(0, len(parts), 6):
        lines.append("".join(parts[index : index + 6]))
    return "\n".join(lines)


def plot_block(rows_by_scenario, key, integer=False, start_year=None):
    base = coordinates(rows_by_scenario["base"], key, integer, start_year)
    emig = coordinates(rows_by_scenario["emigration_constant"], key, integer, start_year)
    inmigr = coordinates(rows_by_scenario["inmigration_constant"], key, integer, start_year)
    return rf"""\addplot[blue, mark=none] coordinates {{
{base}
}};
\addlegendentry{{Escenario base}}
\addplot[red, dashed, mark=none] coordinates {{
{emig}
}};
\addlegendentry{{Emigración constante}}
\addplot[green!60!black, dash pattern=on 5pt off 2pt on 1pt off 2pt, mark=none] coordinates {{
{inmigr}
}};
\addlegendentry{{Inmigración constante}}"""


def figure(metric, rows_by_scenario):
    start = metric.get("start_year", 2018)
    xmin = start
    xmax = 2070
    xticks = (
        "{2023,2028,2033,2038,2043,2048,2053,2058,2063,2068}"
        if start == 2023
        else "{2018,2023,2028,2033,2038,2043,2048,2053,2058,2063,2068}"
    )
    ytick_style = (
        "yticklabel style={/pgf/number format/.cd,fixed,precision=0,1000 sep={,}},\n"
        "    scaled y ticks=false,"
        if metric["integer"]
        else "scaled y ticks=false,"
    )
    return rf"""\begin{{figure}}[htbp]
\centering
\begin{{tikzpicture}}
\begin{{axis}}[
    width=15cm,
    height=8cm,
    xlabel={{Año}},
    ylabel={{{metric['ylabel']}}},
    xmin={xmin}, xmax={xmax},
    ymin={metric['ymin']}, ymax={metric['ymax']},
    xtick={xticks},
    xticklabel style={{rotate=45, anchor=east}},
    {ytick_style}
    grid=both,
    major grid style={{dashed, gray!50}},
    minor grid style={{gray!20}},
    legend style={{at={{(0.5,-0.18)}},anchor=north,legend columns=3,draw=none}},
    line width=1pt
]
{plot_block(rows_by_scenario, metric['key'], metric['integer'], metric.get('start_year'))}
\end{{axis}}
\end{{tikzpicture}}
\caption{{{metric['caption']}}}
\label{{{metric['label']}}}
\vspace{{0.2cm}}
\par\footnotesize{{\textit{{Fuente: cálculos propios.}}}}
\end{{figure}}"""


def migration_coordinates(migration, key):
    parts = [f"({row['year']},{coord_value(row[key], True)})" for row in migration]
    lines = []
    for index in range(0, len(parts), 6):
        lines.append("    " + "\n    ".join(parts[index : index + 6]))
    return "\n".join(lines)


def migration_section(result):
    migration = result["migration"]
    base = migration_coordinates(migration, "base")
    emig = migration_coordinates(migration, "emigration_constant_balance")
    inmigr = migration_coordinates(migration, "inmigration_constant_balance")
    constant = tex_int(result["assumptions"]["constant_inmigration_2020_2025_average"])
    return rf"""\subsection{{Escenarios para la migración neta}}
% ============================================================

El ejercicio toma como escenario base las proyecciones de población del DANE y construye dos escenarios alternativos que modifican únicamente la trayectoria del saldo migratorio internacional. En ambos casos, la población proyectada por el DANE se conserva como trayectoria de referencia y el efecto de cada supuesto migratorio se introduce como una desviación por edad y sexo que se propaga en el tiempo mediante las razones de sobrevivencia.

El primer escenario alternativo corresponde a una \textit{{emigración constante}}. En este caso, la migración neta coincide con la trayectoria base hasta 2027. A partir de 2028, el saldo migratorio continúa deteriorándose al mismo ritmo observado entre 2026 y 2027, y se trunca cuando alcanza un piso de $-140{{.}}000$ personas anuales:

\begin{{equation}}
\label{{eq:ascmig_emig}}
M^{{E}}(t+1)=\max\left\lbrace 1{{,}}5\,M^{{E}}(t),-140{{.}}000\right\rbrace .
\end{{equation}}

El segundo escenario corresponde a una \textit{{inmigración constante}}. Dado que el libro de cálculo no separa de manera directa inmigración bruta y emigración bruta, se adopta un supuesto operativo simétrico al ejercicio anterior: hasta 2027 la trayectoria coincide con la base, y desde 2028 el saldo migratorio alternativo se fija en un flujo positivo constante igual al promedio observado en la serie base entre 2020 y 2025. Este valor es de aproximadamente {constant} personas por año:

\begin{{equation}}
\label{{eq:ascmig_inmig}}
M^{{I}}(t)=\bar{{M}}_{{2020-2025}}=154{{.}}500, \qquad t\geq 2028 .
\end{{equation}}

La Figura \ref{{fig:saldo_migratorio_escenarios}} presenta las trayectorias migratorias utilizadas en el ejercicio.

\begin{{figure}}[htbp]
\centering
\caption{{Saldo neto migratorio en los escenarios base, emigración constante e inmigración constante, 2018--2070.}}
\label{{fig:saldo_migratorio_escenarios}}
\begin{{tikzpicture}}
\begin{{axis}}[
    width=15cm,
    height=8cm,
    xlabel={{Año}},
    ylabel={{Saldo neto migratorio}},
    xmin=2018, xmax=2070,
    ymin=-200000, ymax=800000,
    xtick={{2018,2023,2028,2033,2038,2043,2048,2053,2058,2063,2068}},
    xticklabel style={{rotate=45, anchor=east}},
    yticklabel style={{
        /pgf/number format/.cd,
        fixed,
        precision=0,
        1000 sep={{,}}
    }},
    scaled y ticks=false,
    grid=both,
    major grid style={{dashed, gray!50}},
    minor grid style={{gray!20}},
    legend style={{
        at={{(0.5,-0.18)}},
        anchor=north,
        legend columns=3,
        draw=none
    }},
    line width=1pt
]

\addplot[blue, mark=none] coordinates {{
{base}
}};
\addlegendentry{{Escenario base}}

\addplot[red, dashed, mark=none] coordinates {{
{emig}
}};
\addlegendentry{{Emigración constante}}

\addplot[green!60!black, dash pattern=on 5pt off 2pt on 1pt off 2pt, mark=none] coordinates {{
{inmigr}
}};
\addlegendentry{{Inmigración constante}}

\end{{axis}}
\end{{tikzpicture}}
\vspace{{0.2cm}}
\par\footnotesize{{\textit{{Fuente: DANE y cálculos propios.}}}}
\end{{figure}}

La comparación entre escenarios permite aislar dos riesgos migratorios de signo opuesto. El escenario de emigración constante captura una salida neta persistente de población, mientras que el escenario de inmigración constante representa una entrada neta positiva sostenida. En ambos casos, el efecto relevante no proviene solo del número agregado de migrantes, sino también de su composición por edad y sexo y de la forma como esa desviación se acumula en las cohortes futuras.

"""


METRICS = [
    {
        "subsection": "Población total",
        "key": "total",
        "ylabel": "Población total",
        "caption": "Población total en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_pob_total",
        "integer": True,
        "ymin": 45000000,
        "ymax": 60000000,
        "text": "La población total resume el volumen agregado de habitantes bajo cada trayectoria migratoria. La emigración constante reduce de forma persistente el tamaño de la población, mientras que la inmigración constante desplaza la trayectoria hacia arriba y retrasa parcialmente la caída demográfica de largo plazo.",
    },
    {
        "subsection": "Población en edad de trabajar (PET)",
        "key": "pet",
        "ylabel": "PET",
        "caption": "Población en edad de trabajar (PET) en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_pet",
        "integer": True,
        "ymin": 40000000,
        "ymax": 52500000,
        "text": "La PET, definida en este ejercicio como la población de 15 años o más, aproxima la base demográfica potencial del mercado laboral. El escenario de emigración constante erosiona esa base, mientras que el escenario de inmigración constante la amplía de manera sostenida.",
    },
    {
        "subsection": "Población económicamente activa (PEA)",
        "key": "pea",
        "ylabel": "PEA",
        "caption": "Población económicamente activa (PEA) en los escenarios base, emigración constante e inmigración constante, 2023--2070.",
        "label": "fig:res_pea",
        "integer": True,
        "ymin": 24000000,
        "ymax": 36500000,
        "start_year": 2023,
        "text": "La PEA combina la estructura demográfica con las matrices de participación laboral por edad y sexo. Por esta razón, el efecto migratorio se transmite tanto por el tamaño de las cohortes como por su localización dentro del ciclo laboral.",
    },
    {
        "subsection": "Dependencia total",
        "key": "dep_total",
        "ylabel": "Dependencia total",
        "caption": "Dependencia total en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_dep_total",
        "integer": False,
        "ymin": 0.43,
        "ymax": 0.72,
        "text": "La dependencia total relaciona la población de 0 a 14 años y de 65 años o más con la población de 15 a 64 años. La emigración constante aumenta esta carga relativa en el largo plazo, mientras que la inmigración constante la modera al ampliar la población en edades centrales.",
    },
    {
        "subsection": "Dependencia juvenil",
        "key": "dep_young",
        "ylabel": "Dependencia juvenil",
        "caption": "Dependencia juvenil en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_dep_juv",
        "integer": False,
        "ymin": 0.14,
        "ymax": 0.39,
        "text": "La dependencia juvenil mantiene una tendencia descendente en todos los escenarios. La emigración constante atenúa esa reducción porque disminuye la población de 15 a 64 años, mientras que la inmigración constante refuerza la caída relativa del indicador.",
    },
    {
        "subsection": "Dependencia senil",
        "key": "dep_old",
        "ylabel": "Dependencia senil",
        "caption": "Dependencia senil en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_dep_sen",
        "integer": False,
        "ymin": 0.13,
        "ymax": 0.52,
        "text": "La dependencia senil crece de forma sostenida en todos los escenarios, reflejando el envejecimiento estructural de la población. La inmigración constante no elimina esa tendencia, pero reduce la presión relativa sobre la población en edades de trabajo frente al escenario base y, especialmente, frente al escenario de emigración constante.",
    },
    {
        "subsection": "Índice de envejecimiento",
        "key": "aging_index",
        "ylabel": "Índice de envejecimiento",
        "caption": "Índice de envejecimiento en los escenarios base, emigración constante e inmigración constante, 2018--2070.",
        "label": "fig:res_ind_env",
        "integer": False,
        "ymin": 0.35,
        "ymax": 3.25,
        "text": "El índice de envejecimiento relaciona la población de 65 años o más con la población menor de 15 años. En contraste con las tasas de dependencia, la inmigración constante puede elevar este cociente en el largo plazo porque las cohortes adicionales incorporadas durante el horizonte de proyección también envejecen y terminan aumentando el numerador del indicador.",
    },
]


def results_section(result):
    rows_by_scenario = {
        "base": result["base"],
        "emigration_constant": result["emigration_constant"],
        "inmigration_constant": result["inmigration_constant"],
    }
    indexed = {
        name: {row["year"]: row for row in rows}
        for name, rows in rows_by_scenario.items()
    }
    sections = [
        r"""\section{Resultados}

La presente sección compara la evolución de los principales indicadores demográficos y laborales bajo tres trayectorias: el escenario base del DANE, un escenario de emigración constante y un escenario de inmigración constante. En todos los casos, los escenarios alternativos preservan la estructura metodológica del ejercicio inicial: se modifica el saldo migratorio agregado, se distribuye el diferencial por edad y sexo, y luego se propaga el efecto por cohortes mediante razones de sobrevivencia.

"""
    ]

    for metric in METRICS:
        base_2070 = indexed["base"][2070][metric["key"]]
        emig_2070 = indexed["emigration_constant"][2070][metric["key"]]
        inmigr_2070 = indexed["inmigration_constant"][2070][metric["key"]]
        value_text = (
            f"{tex_int(base_2070)}, {tex_int(emig_2070)} y {tex_int(inmigr_2070)}"
            if metric["integer"]
            else f"{base_2070:.4f}, {emig_2070:.4f} y {inmigr_2070:.4f}"
        )
        sections.append(
            rf"""\subsection{{{metric['subsection']}}}

{figure(metric, rows_by_scenario)}

{metric['text']} En 2070, los valores correspondientes al escenario base, al escenario de emigración constante y al escenario de inmigración constante son, respectivamente, {value_text}.

"""
        )

    sections.append(
        r"""\subsection{Síntesis}

En conjunto, los resultados muestran que los supuestos migratorios alteran tanto el tamaño de la población como la composición de las cohortes que sostienen el mercado laboral y la carga demográfica. El escenario de emigración constante reduce la población total, la PET y la PEA, y aumenta las tasas de dependencia total, juvenil y senil frente al escenario base. El escenario de inmigración constante opera en la dirección opuesta para esos indicadores: incrementa la población y la fuerza laboral potencial, y reduce la presión relativa sobre la población de 15 a 64 años.

Sin embargo, el índice de envejecimiento muestra que una mayor inmigración no equivale necesariamente a una estructura permanentemente más joven. Bajo el supuesto operativo utilizado, las cohortes adicionales también envejecen dentro del horizonte de proyección, por lo que el cociente entre población mayor y población infantil puede terminar siendo más alto en el escenario de inmigración constante. Este resultado subraya que el efecto de la migración depende no solo del volumen neto de personas, sino de su distribución por edad y de la dinámica acumulada de las cohortes.

"""
    )
    return "".join(sections)


def conclusions_section():
    return r"""\section{Conclusiones}

Los resultados muestran que Colombia enfrenta una transición demográfica profunda, caracterizada por la pérdida gradual del peso relativo de la población joven y el aumento sostenido de la población mayor. En una primera etapa, esta transformación reduce la tasa de dependencia total debido a la caída de la dependencia juvenil. Sin embargo, esa mejora es transitoria: a medida que avanza el horizonte de proyección, el aumento de la dependencia senil más que compensa la reducción del componente juvenil, y la carga demográfica total vuelve a incrementarse.

La comparación entre escenarios permite identificar la sensibilidad de esta trayectoria a diferentes supuestos migratorios. Una emigración neta persistentemente alta reduce la población total, la población en edad de trabajar y la población económicamente activa, al tiempo que eleva las tasas de dependencia. En contraste, una inmigración neta positiva y sostenida aumenta la base demográfica y laboral, y modera parte de la presión sobre la población de 15 a 64 años.

No obstante, ninguno de los escenarios elimina el proceso de envejecimiento. La migración cambia el nivel y la velocidad de algunos indicadores, pero la dinámica central sigue determinada por la estructura etaria acumulada de la población. Desde una perspectiva económica y fiscal, esto implica que las políticas de mercado laboral, pensiones, salud y cuidado deberán considerar no solo el volumen agregado de la migración, sino también su composición por edad y sexo y su persistencia en el tiempo.

"""


def main():
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    text = MAIN.read_text(encoding="utf-8")

    text = text.replace(
        "Las proyecciones oficiales del DANE asumen que el saldo migratorio internacional converge gradualmente a cero después de 2030. Esta proyección implica que la migración deja de ser un factor relevante en la dinámica poblacional a partir de la próxima década. Sin embargo, vale la pena evaluar un escenario de riesgo donde la inmigración se reduce a cero pero las tendencias de emigración se mantienen.  Ese es el objetivo del presente trabajo.",
        "Las proyecciones oficiales del DANE asumen que el saldo migratorio internacional converge gradualmente a valores cercanos a cero en el largo plazo. Esta trayectoria implica que la migración deja de ser un factor decisivo en la dinámica poblacional después de la próxima década. Sin embargo, vale la pena evaluar escenarios alternativos en los que los flujos migratorios no se extinguen: uno de emigración neta persistente y otro de inmigración neta sostenida. Ese es el objetivo del presente trabajo.",
    )

    text = text.replace(
        r"""\noindent Las proyecciones oficiales de población del DANE asumen que el saldo migratorio internacional de Colombia converge a cero después de 2030. Este supuesto trata la migración como un fenómeno transitorio que se extingue. El presente documento propone un escenario alternativo donde la inmigración se extingue pero la emigración anual se mantiene en niveles similares a los del quinquenio 2020-2025. A partir de la descomposición de esta emigración por edades, se cuantifica su impacto sobre la población total, la población en edad de trabajar, la fuerza laboral, tasa de dependencia, el índice de envejecimiento y otras variables sociodemográficas en el horizonte 2025--2070. \\[0.3cm]""",
        r"""\noindent Las proyecciones oficiales de población del DANE asumen que el saldo migratorio internacional de Colombia converge a valores cercanos a cero en el largo plazo. Este supuesto trata la migración como un fenómeno transitorio que se extingue. El presente documento compara esa trayectoria con dos escenarios alternativos: uno donde la emigración neta se mantiene elevada de forma persistente y otro donde la inmigración neta permanece en niveles similares a los observados en el quinquenio 2020--2025. A partir de la descomposición de los flujos migratorios por edad y sexo, se cuantifica su impacto sobre la población total, la población en edad de trabajar, la fuerza laboral, las tasas de dependencia y el índice de envejecimiento en el horizonte 2025--2070. \\[0.3cm]""",
    )

    text = text.replace(
        "Para ambos escenarios se asume que la población de cada edad y sexo se actualiza anualmente en función de la población del año anterior, la sobrevivencia y la migración neta:",
        "Para los escenarios considerados se asume que la población de cada edad y sexo se actualiza anualmente en función de la población del año anterior, la sobrevivencia y la migración neta:",
    )

    start = text.index(r"\subsection{Escenarios para la migración neta}")
    end = text.index(r"\subsection{Descomposición de la migración neta}")
    text = text[:start] + migration_section(result) + text[end:]

    marker = r"\label{eq:descmig}" + "\n" + r"M_{x,s}(t) = \pi_{x,s} \sum_s \sum_x M_{x}(t)" + "\n" + r"\end{equation}"
    replacement = marker + "\n\n" + (
        "En el escenario de inmigración constante se aplica la misma matriz de distribución por edad y sexo como supuesto operativo. "
        "Esta decisión mantiene la comparabilidad con el escenario de emigración constante, aunque debe interpretarse como una aproximación "
        "ante la ausencia de una matriz separada de inmigración bruta por edad y sexo en el libro de cálculo."
    )
    text = text.replace(marker, replacement)

    results_start = text.index(r"\section{Resultados}")
    document_end = text.index(r"\end{document}")
    text = text[:results_start] + results_section(result) + conclusions_section() + text[document_end:]

    MAIN.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
