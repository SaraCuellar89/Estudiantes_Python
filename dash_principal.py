import pandas as pd
import plotly.express as px
import os
import dash
from dash import html, dcc, Input, Output, dash_table
from database import Obtener_Estudiantes
from flask import session


def crear_tablero(server):

    # ===================== Inicializar app =====================
    appnotas = dash.Dash(__name__, server=server, url_base_pathname="/dash_principal/", suppress_callback_exceptions=True)

    # ===================== Cargar datos iniciales =====================
    _init = Obtener_Estudiantes()

    # ===================== Renderizado del dashboard =====================
    appnotas.layout = html.Div([
        
        html.H1("Dashboard de Notas", style={
            "textAlign": "center",
            "backgroundColor": "#1F2022",
            "color": "white",
            "padding": "20px",
            "borderRadius": "10px"
        }),

        # --------- Contenedor de filtros ---------
        html.Div([
            html.Label("Seleccionar carrera:", style={"fontWeight": "bold"}),
            
            # --------- Filtro de carrera ---------
            dcc.Dropdown(
                id="filtro_carrera",
                options=[{"label": "Todas", "value": "Todas"}] +
                        [{"label": c, "value": c} for c in sorted(_init["carrera"].unique())],
                value="Todas"
            ),
            
            html.Br(),
            
            html.Label("Rango de edad:", style={"fontWeight": "bold"}),
             
            # --------- Filtro de edad --------- 
            dcc.RangeSlider(
                id="slider_edad",
                step=1,
                min=int(_init["edad"].min()),
                max=int(_init["edad"].max()),
                value=[int(_init["edad"].min()), int(_init["edad"].max())],
                marks={i: str(i) for i in range(int(_init["edad"].min()), int(_init["edad"].max()) + 1, 5)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),

            html.Br(),
            
            html.Label("Rango promedio:", style={"fontWeight": "bold"}),
            dcc.RangeSlider(
                id="slider_promedio",
                min=0,
                max=5,
                step=0.1,
                value=[0, 5],
                tooltip={"placement": "bottom", "always_visible": True}
            ),

        ], style={"width": "80%", "margin": "auto", "padding": "20px", "border": "1px solid #ccc", "borderRadius": "10px"}),
        
        html.Br(),
        
        # --------- Contenedor de KPIS ---------
        html.Div(id="kpis", style={
            "display": "flex",
            "justifyContent": "space-around"
        }),
        
        html.Br(),
        
        # --------- Barra de Busqueda ---------
        dcc.Input(
            id="busqueda",
            type="text",
            placeholder="Buscar Estudiante...",
            style={
                'marginBottom': "40px",
                'marginTop': "20px"
            }
        ),
        
        html.Br(),
        
        dcc.Interval(
            id="intervalo",
            interval=30000,
            n_intervals=0
        ),
        
        # --------- Tabla con todos los estudiantes ---------
        dcc.Loading(
            children=[
                dash_table.DataTable(
                    id="Tabla",
                    page_size=8,
                    filter_action="native",
                    sort_action="native",
                    row_selectable="multi",
                    selected_rows=[],
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "center", "padding": "10px"},
                    style_header={"backgroundColor": "#000000", "fontWeight": "bold", "color": "white"}
                )
            ],
            type="circle" 
        ),
        
        html.Br(),
        
        dcc.Graph(id="gran_detallado"),
        
        # --------- Pestañas para ver las graficas ---------
        dcc.Tabs([
            dcc.Tab(label="Histograma Promedios", children=[dcc.Graph(id="histograma")]), 
            dcc.Tab(label="Dispersión Edad vs Nota", children=[dcc.Graph(id="dispersion")]), 
            dcc.Tab(label="Desempeño (Pie)", children=[dcc.Graph(id="pie")]),           
            dcc.Tab(label="Promedio por Carrera", children=[dcc.Graph(id="promedio_carrera")])           
        ]),

        html.Br(),

        # --------- Tabla de los mejos 10 estudiantes ---------
        html.H3("Top 10 Mejores Estudiantes", style={"textAlign": "center"}),
        dash_table.DataTable(
            id="ranking",
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "padding": "10px"},
            style_header={"backgroundColor": "#20221F", "color": "white", "fontWeight": "bold"},
            style_data={
                "backgroundColor": "#C5EEC5",  # verde claro
                "color": "black"
            },
        ),

        html.Br(),

        # --------- Tabla con estudiantes en riesgo (promedio menor a 3) ---------
        html.H3("Estudiantes en Riesgo", style={"textAlign": "center"}),
        dash_table.DataTable(
            id="riesgo",
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "padding": "10px"},
            style_header={"backgroundColor": "#1F2022", "color": "white", "fontWeight": "bold"},
            style_data={
                "backgroundColor": "#EEC5C5",  # verde claro
                "color": "black"
            },
        ),
        
        # --------- Boton para cerrar sesion ---------
        html.A("Cerrar Sesión",
            href="/cerrar_sesion",
            style={
                "position": "absolute",
                "right": "20px",
                "top": "40px",
                "backgroundColor": "#000000",
                "color": "white",
                "padding": "10px 20px",
                "borderRadius": "5px",
                "textDecoration": "none",
                "fontWeight": "bold"
            }
        ), 
        
        # --------- Boton para registrar estudiantes ---------
        html.A("Registrar Estudiante",
            href="/opciones_registro",
            style={
                "position": "absolute",
                "left": "20px",
                "top": "40px",
                "backgroundColor": "#000000",
                "color": "white",
                "padding": "10px 20px",
                "borderRadius": "5px",
                "textDecoration": "none",
                "fontWeight": "bold"
            }
        ), 

    ], style={"fontFamily": "Arial"}) 


    # ===================== Callback y funcion para actualizar la tabla de todos los estudiantes =====================
    @appnotas.callback(
        Output("gran_detallado", "figure"),
        Input("Tabla", "derived_virtual_data"),
        Input("Tabla", "derived_virtual_selected_rows"),
        Input("intervalo", "n_intervals"),
    )


    def actualizar_tabla(rows, selected_rows, n_intervals):

        if not rows:
            return px.scatter(title="Sin datos")

        dff = pd.DataFrame(rows)

        if dff.empty:
            return px.scatter(title="Sin datos")

        if selected_rows:
            dff = dff.iloc[selected_rows]

        fig = px.scatter(dff, x="edad", y="promedio", color="desempeno", size="promedio", title="Análisis Detallado (Selecciona filas en la tabla)")

        return fig
    
    
    # ===================== Callback y funcion para actualizar el dropdown de las carreras =====================
    @appnotas.callback(
        Output("filtro_carrera", "options"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_opciones_carrera(n_intervals):
        dataf = Obtener_Estudiantes()
        carreras = sorted(dataf["carrera"].unique())
        return [{"label": "Todas", "value": "Todas"}] + \
            [{"label": c, "value": c} for c in carreras]
            
        
    # ===================== Callback y funcion para actualizar el dropdown de las edades =====================  
    @appnotas.callback(
        Output("slider_edad", "min"),
        Output("slider_edad", "max"),
        Output("slider_edad", "value"),
        Output("slider_edad", "marks"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_slider_edad(n_intervals):
        dataf = Obtener_Estudiantes()
        min_e = int(dataf["edad"].min())
        max_e = int(dataf["edad"].max())
        marks = {i: str(i) for i in range(min_e, max_e + 1, 5)}
        return min_e, max_e, [min_e, max_e], marks
           


    # ===================== Callback y funcion para actualizar el grafico de KPIS  =====================
    @appnotas.callback(
        Output("Tabla", "data"),
        Output("Tabla", "columns"),
        Output("kpis", "children"),
        Input("filtro_carrera", "value"),
        Input("slider_edad", "value"),
        Input("slider_promedio", "value"),
        Input("busqueda", "value"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_comp(carrera, rangoedad, rangoprome, busqueda, n_intervals):
        
        if rangoedad is None or rangoprome is None:
            return [], [], []
        
        dataf = Obtener_Estudiantes()
        
        # Filtrado de datos
        if carrera == "Todas":
            filtro = dataf[
                (dataf["edad"] >= rangoedad[0]) &
                (dataf["edad"] <= rangoedad[1]) &
                (dataf["promedio"] >= rangoprome[0]) &
                (dataf["promedio"] <= rangoprome[1])
            ]
        else:
            filtro = dataf[
                (dataf["carrera"] == carrera) & 
                (dataf["edad"] >= rangoedad[0]) &
                (dataf["edad"] <= rangoedad[1]) &
                (dataf["promedio"] >= rangoprome[0]) &
                (dataf["promedio"] <= rangoprome[1])
            ]
    
        # Filtro de busqueda
        if busqueda:
            filtro = filtro[filtro.apply(lambda row: busqueda.lower() in str(row).lower(), axis=1)]

        # Cálculo de métricas
        if not filtro.empty:
            promedio_val = round(filtro["promedio"].mean(), 2)
            total_val = len(filtro)
            maximo_val = round(filtro["promedio"].max(), 2)
        else:
            promedio_val = total_val = maximo_val = 0

        # Creación de los componentes de KPI
        estilo_kpi = {
            "backgroundColor": "#1F2022", "color": "white",
            "padding": "20px", "borderRadius": "10px", 
            "textAlign": "center", "width": "25%"
        }

        kpis_html = [
            html.Div([html.H4("Promedio"), html.H2(promedio_val)], style=estilo_kpi),
            html.Div([html.H4("Total Estudiantes"), html.H2(total_val)], style=estilo_kpi),
            html.Div([html.H4("Nota Máxima"), html.H2(maximo_val)], style=estilo_kpi),
        ]

        columnas = [{"name": i, "id": i} for i in filtro.columns]
        
        return filtro.to_dict("records"), columnas, kpis_html


    # ===================== Callback y funcion para actualizar los graficos de las pestañas =====================
    @appnotas.callback(
        Output("histograma", "figure"),
        Output("dispersion", "figure"),
        Output("pie", "figure"),
        Output("promedio_carrera", "figure"),
        Input("filtro_carrera", "value"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_graficos(carrera, n_intervals):
        
        if carrera is None:
            carrera = "Todas"
        
        dataf = Obtener_Estudiantes()

        if carrera == "Todas":
            df_carrera = dataf
        else:
            df_carrera = dataf[dataf["carrera"] == carrera]
        
        fig_hist = px.histogram(df_carrera, x="promedio", title="Distribución de Promedios", color_discrete_sequence=['#4251A7'])
        fig_disp = px.scatter(df_carrera, x="edad", y="promedio", title="Edad vs Promedio", color="desempeno")  # minúscula
        fig_pie = px.pie(df_carrera, names="desempeno", title="Proporción por Desempeño")
        fig_prom_car = px.bar(dataf, x="carrera", y="promedio", title="Promedio por Carrera", color="carrera")  # minúscula

        return fig_hist, fig_disp, fig_pie, fig_prom_car
    

    # ===================== Callback y funcion para actualizar la tabla de top 10 mejores estudiantes =====================
    @appnotas.callback(
        Output("ranking", "data"),
        Output("ranking", "columns"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_ranking(n_intervals):
        dataf = Obtener_Estudiantes()
        
        top10 = dataf[["nombre", "carrera", "promedio"]] \
                    .sort_values("promedio", ascending=False) \
                    .head(10) \
                    .reset_index(drop=True)
        
        top10.index += 1  # posición desde 1
        top10.insert(0, "posicion", top10.index)

        columnas = [{"name": i.capitalize(), "id": i} for i in top10.columns]
        
        return top10.to_dict("records"), columnas


    # ===================== Callback y funcion para actualizar la tabla de estudiantes en riesgo =====================
    @appnotas.callback(
        Output("riesgo", "data"),
        Output("riesgo", "columns"),
        Input("intervalo", "n_intervals"),
    )
    def actualizar_estudiantes_riesgo(n_intervals):
        dataf = Obtener_Estudiantes()
        
        riesgo = dataf[dataf["promedio"] < 3.0][["nombre", "carrera", "promedio"]] \
                    .sort_values("promedio", ascending=True) \
                    .reset_index(drop=True)
        
        riesgo.index += 1
        riesgo.insert(0, "posicion", riesgo.index)

        columnas = [{"name": i.capitalize(), "id": i} for i in riesgo.columns]
        
        return riesgo.to_dict("records"), columnas
    
    
    # ===================== Exportacion de todo el dashboard =====================
    return appnotas