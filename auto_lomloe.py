#!/usr/bin/env python3
import argparse
import os
import pandas as pd


def preparar_mapeo(mapping_path, sheet_name="Esquema elementos currículo"):
    # --- Paso 1: Cargar y limpiar el mapeo curricular con forward-fill ---
    mapeo = pd.read_excel(
        mapping_path,
        sheet_name=sheet_name,
        usecols=[
            "Competencias específicas",
            "Descriptores del perfil de salida",
            "Criterios de evaluación",
            "Saberes básicos",
        ],
        dtype=str,
    )

    # Forward-fill para propagar valores de celdas unidas
    mapeo[
        [
            "Competencias específicas",
            "Descriptores del perfil de salida",
            "Criterios de evaluación",
        ]
    ] = mapeo[
        [
            "Competencias específicas",
            "Descriptores del perfil de salida",
            "Criterios de evaluación",
        ]
    ].ffill()

    # --- Paso 2: Agrupar para capturar múltiples asociaciones ---
    agrupado = (
        mapeo.groupby("Saberes básicos")
        .agg(
            {
                "Competencias específicas": lambda vals: sorted(
                    {str(v) for v in vals if pd.notna(v)}
                ),
                "Descriptores del perfil de salida": lambda vals: sorted(
                    {v for v in vals if pd.notna(v)}
                ),
                "Criterios de evaluación": lambda vals: sorted(
                    {v for v in vals if pd.notna(v)}
                ),
            }
        )
        .reset_index()
    )

    # Convertir a diccionarios de listas
    dict_competencias = agrupado.set_index("Saberes básicos")[
        "Competencias específicas"
    ].to_dict()
    dict_descriptores = agrupado.set_index("Saberes básicos")[
        "Descriptores del perfil de salida"
    ].to_dict()
    dict_criterios = agrupado.set_index("Saberes básicos")[
        "Criterios de evaluación"
    ].to_dict()

    return dict_competencias, dict_descriptores, dict_criterios

# --- Paso 3: Función para rellenar campos considerando múltiples asociaciones ---
def rellenar_campos(saberes_str, dict_competencias, dict_descriptores, dict_criterios):
    if pd.isna(saberes_str):
        return "", "", ""
    saberes = [s.strip() for s in saberes_str.split(", ")]
    competencias = []
    descriptores = []
    criterios = []
    for s in saberes:
        competencias.extend(dict_competencias.get(s, []))
        descriptores.extend(dict_descriptores.get(s, []))
        criterios.extend(dict_criterios.get(s, []))
    # Deduplicar y ordenar
    competencias = sorted(set(", ".join(competencias).split(", ")))
    descriptores = sorted(set(", ".join(descriptores).split(", ")))
    criterios = sorted(set(", ".join(criterios).split(", ")))
    # Devolver como cadenas
    return (
        ", ".join(competencias),
        ", ".join(descriptores),
        ", ".join(criterios),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Rellena automáticamente competencias, descriptores y criterios "
        "a partir de un mapeo curricular."
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="Excel de mapeo curricular (con hoja 'Descripción elementos del currí').",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Excel incompleto con columnas 'Nº actividad' y 'Saberes básicos'.",
    )
    parser.add_argument(
        "--index",
        required=False,
        help="Nombre de la columna que se usará como índice (por defecto: 'Nº carta').",
        default="Nº carta",
    )
    args = parser.parse_args()

    # Preparar mapeo
    dict_comp, dict_desc, dict_crit = preparar_mapeo(args.mapping)
    
# --- Paso 4: Leer archivo de entrada ---
    df = pd.read_excel(args.input, dtype=str, index_col=args.index)
    # Verificar que la columna "Saberes básicos" existe
    if "Saberes básicos" not in df.columns:
        raise KeyError(
            "El archivo de entrada debe tener una columna llamada 'Saberes básicos'."
        )

# --- Paso 5: Aplicar función y generar columnas nuevas ---
    df[
        ["Competencias específicas", "Descriptores del perfil de salida", "Criterios de evaluación"]
    ] = df["Saberes básicos"].apply(
        lambda s: pd.Series(rellenar_campos(s, dict_comp, dict_desc, dict_crit))
    )

    # Construir nombre de salida
    base, ext = os.path.splitext(args.input)
    output_path = f"{base}_filled{ext}"

    # Guardar resultado
    df.to_excel(output_path, index=True)
    print(f"Archivo generado: {output_path}")


if __name__ == "__main__":
    main()
