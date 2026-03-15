from flask import Flask, render_template, request, redirect, jsonify, session, send_file
import mysql.connector
from database import conectar, Obtener_Usuario, Insertar_Estudiante, buscar_estudiante, Obtener_Estudiantes, obtener_carreras
from dash_principal import crear_tablero
import pandas as pd
import unicodedata


app = Flask(__name__)
app.secret_key = "contrasena_1234"
dash_app = crear_tablero(app)

# ===================== Rutas =====================
# Saludo
@app.route("/saludar")
def saludar():
    return jsonify({"message": "Servirdor Flask Corriendo Correctamente"})


# Evitar cache en paginas protegidas
@app.after_request
def agregar_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Proteger rutas del dashboard
@app.before_request
def proteger_rutas():

    rutas_protegidas = ["/dash_principal"]

    if any(request.path.startswith(ruta) for ruta in rutas_protegidas):
        if "usuario" not in session:
            return redirect("/")


# Inicio de Sesion
@app.route("/", methods=['GET','POST'])
def iniciar_sesion():
    try:
        # Verificar si el formulario fue enviado
        if request.method == 'POST':
            nombre_usuario = request.form['nombre_usuario']
            contrasena = request.form['contrasena']
        
            usuario = Obtener_Usuario(nombre_usuario)
            
            if not usuario:
                return "Usuario Inexistente"
            
            if usuario["contrasena"] != contrasena:
                return "Contraseña incorrecta"
                
            session['usuario'] = {
                "id": usuario['id_usuario'],
                "nombre": usuario['nombre_usuario'],
                "rol_usuario": usuario['rol_usuario']
            }

            return redirect('/dash_principal')
                
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    
    return render_template("inicio_sesion.html")


# Cerrar Sesion
@app.route("/cerrar_sesion")
def logout():
    session.clear()
    return redirect("/")


# Ir a opciones de registro
@app.route("/opciones_registro")
def ir_opciones():
    return render_template("opciones.html")


# Registro de un estudiante
@app.route("/registrar_estudiante", methods=["GET", "POST"])
def registrar_estudiante():
    
    if "usuario" not in session:
        return redirect("/")
    
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            edad = request.form['edad']
            carrera = request.form['carrera']
            nota_1 = float(request.form['nota_1'])
            nota_2 = float(request.form['nota_2'])
            nota_3 = float(request.form['nota_3'])

            existe = buscar_estudiante(nombre, carrera)

            if existe:
                return render_template(
                    "fomu_registro_estudiante.html",
                    error="Ese estudiante ya existe"
                )
                
            promedio = round((nota_1 + nota_2 + nota_3) / 3, 2)
            desempeno = calcular_desempeno(promedio)
                
            Insertar_Estudiante(nombre, edad, carrera, nota_1, nota_2, nota_3, promedio, desempeno)

            return redirect('/dash_principal')
                
        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            }), 500
    
    return render_template("fomu_registro_estudiante.html")


# Carga Masiva
@app.route("/carga_masiva", methods=["GET", "POST"])
def cargar_datos_masivos():
    if request.method == "POST":
        archivo = request.files["archivo"]
        
        # --- leer archivo ---
        df = pd.read_excel(archivo)
        df = df.drop(columns=["id_usuario"], errors="ignore") 
        
        # --- limpiar nombres ---
        df["Nombre"] = df["Nombre"].astype(str).str.strip()
        df["Nombre"] = df["Nombre"].apply(quitar)
        df["Nombre"] = df["Nombre"].str.title()
        
        df["Carrera"] = df["Carrera"].astype(str).str.strip()
        df["Carrera"] = df["Carrera"].apply(quitar)
        df["Carrera"] = df["Carrera"].str.title()

        rechazados = []

        # --- Datos Faltantes ---
        faltantes = df[df.isnull().any(axis=1)].copy()
        if not faltantes.empty:
            faltantes["Motivo"] = "Datos faltantes"
            rechazados.append(faltantes)
        df = df.dropna()
         

        # --- Edad Negativa ---
        edad_negativa = df[df["Edad"] < 0].copy()
        if not edad_negativa.empty:
            edad_negativa["Motivo"] = "Edad negativa"
            rechazados.append(edad_negativa)
        df = df[df["Edad"] >= 0]
        

        # --- Notas Invalidas ---
        notas_invalidas = df[
            ~(
                (df["Nota1"] >= 0) & (df["Nota1"] <= 5) &
                (df["Nota2"] >= 0) & (df["Nota2"] <= 5) &
                (df["Nota3"] >= 0) & (df["Nota3"] <= 5)
            )
        ].copy()
        if not notas_invalidas.empty:
            notas_invalidas["Motivo"] = "Notas inválidas"
            rechazados.append(notas_invalidas)
        df = df[
            (df["Nota1"] >= 0) & (df["Nota1"] <= 5) &
            (df["Nota2"] >= 0) & (df["Nota2"] <= 5) &
            (df["Nota3"] >= 0) & (df["Nota3"] <= 5)
        ]
        

        # --- Duplicados del archivo ---
        duplicados = df[df.duplicated(subset=["Nombre", "Carrera"], keep="first")].copy()
        if not duplicados.empty:
            duplicados["Motivo"] = "Duplicado en el archivo"
            rechazados.append(duplicados)
        df = df.drop_duplicates(subset=["Nombre", "Carrera"])


        # --- Estudiantes que ya existen en la bbdd ---
        existentes = Obtener_Estudiantes()[["nombre", "carrera"]]
        mascara = df.apply(
            lambda r: ((existentes["nombre"] == r["Nombre"]) & 
                       (existentes["carrera"] == r["Carrera"])).any(), axis=1
        )
        ya_existentes = df[mascara].copy()
        if not ya_existentes.empty:
            ya_existentes["Motivo"] = "Estudiante ya existe en la base de datos"
            rechazados.append(ya_existentes)
        df = df[~mascara]


        # --- calcular el promedio y desempeño ---
        df["Promedio"] = ((df["Nota1"] + df["Nota2"] + df["Nota3"]) / 3).round(2)
        df = df[df["Promedio"] <= 5]
        
        df["Desempeno"] = df["Promedio"].apply(calcular_desempeno)
        

        # --- Insertar datos ---
        conexion = conectar()
        cursor = conexion.cursor()
        
        query = """INSERT INTO estudiante (nombre, edad, carrera, nota_1, nota_2, nota_3, promedio, desempeno) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"""

        existentes = Obtener_Estudiantes()[["nombre", "carrera"]]
        df = df[~df.apply(lambda r: ((existentes["nombre"] == r["Nombre"]) & (existentes["carrera"] == r["Carrera"])).any(), axis=1)]
        
        for _, row in df.iterrows():
            cursor.execute(query, (
                row["Nombre"],
                row["Edad"],
                row["Carrera"],
                row["Nota1"],
                row["Nota2"],
                row["Nota3"],
                row["Promedio"],
                row["Desempeno"],
            ))
            
        conexion.commit()
        conexion.close()
        

        # --- Contar por categoría ---
        total_insertados = len(df)
        total_faltantes = len(faltantes) if not faltantes.empty else 0
        total_edad = len(edad_negativa) if not edad_negativa.empty else 0
        total_notas = len(notas_invalidas) if not notas_invalidas.empty else 0
        total_duplicados = len(duplicados) if not duplicados.empty else 0
        total_existentes = len(ya_existentes) if not ya_existentes.empty else 0
        total_rechazados = total_faltantes + total_edad + total_notas + total_duplicados + total_existentes


        # --- Generar Archivo de rechazados ---
        if rechazados:
            df_rechazados = pd.concat(rechazados, ignore_index=True)
            ruta = "rechazados.xlsx"
            df_rechazados.to_excel(ruta, index=False)
            hay_rechazados = True
        else:
            hay_rechazados = False

        return render_template("carga_masiva.html",
                            insertados=total_insertados,
                            hay_rechazados=hay_rechazados,
                            resumen=[
                                {"categoria": "Insertados", "cantidad": total_insertados},
                                {"categoria": "Rechazados", "cantidad": total_rechazados},
                                {"categoria": "Duplicados", "cantidad": total_duplicados},
                            ])
        
    return render_template("carga_masiva.html")


# Decargar archivo de reachazados
@app.route("/descargar_rechazados")
def descargar_rechazados():
    return send_file("rechazados.xlsx", as_attachment=True, download_name="rechazados.xlsx")
 

# Funcion para quitar acentos
def quitar(texto):
    if pd.isna(texto):
        return texto
    
    texto = str(texto)
    
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


# Clasificar el desempeño
def calcular_desempeno(promedio):
    if promedio >= 4.5:
        desempeno = "Excelente"
    elif promedio >=4:
        desempeno = "Bueno"
    elif promedio >= 3:
        desempeno = "Regular"
    else:
        desempeno = "Deficiente"
    return desempeno


# Obtener todas las carreras 
@app.route("/obtener_carreras")
def ruta_obtener_carreras():
    carreras = obtener_carreras()
    return jsonify(carreras)


if __name__ == "__main__":
    try:
        conexion = conectar()
        print(" ======= Conexion Exitosa =======")
        conexion.close()
    except Exception as e:
        print("Error al conectar:", e)
    
    print(" ======= Servidor corriendo en: http://127.0.0.1:5000/ =======")
    app.run(debug=True)