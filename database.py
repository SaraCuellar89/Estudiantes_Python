import pandas as pd
import mysql.connector

def conectar():
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="database_analisis_estudiantes"
    )
    
    return conexion


# Obtener usuario
def Obtener_Usuario(nombre_usuario):
    # Conectar a la bbdd
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    
    # Buscar usuario
    cursor.execute('SELECT * FROM usuario WHERE nombre_usuario = %s', (nombre_usuario,))
    usuario = cursor.fetchone()
    
    conexion.close()
    
    return usuario


# Obtener los estudiantes
def Obtener_Estudiantes():
    conexion = conectar()
    query = "SELECT * FROM estudiante"
    
    df = pd.read_sql(query, conexion)
    
    conexion.close()
    
    return df


# Buscar estudiante por nombre y carrera
def buscar_estudiante(nombre, carrera):
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM estudiante WHERE nombre = %s AND carrera = %s', (nombre, carrera))
    estudiante = cursor.fetchone()
    
    conexion.close()
    
    return estudiante


# Registrar estudiante
def Insertar_Estudiante(nombre, edad, carrera, nota_1, nota_2, nota_3, promedio, desempeno):
    conexion = conectar()
    cursor = conexion.cursor()
    
    query = """INSERT INTO estudiante (nombre, edad, carrera, nota_1, nota_2, nota_3, promedio, desempeno) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    cursor.execute(query,(nombre, edad, carrera, nota_1, nota_2, nota_3, promedio, desempeno))
    conexion.commit()
    
    conexion.close()
    

# Obtener todas las carreras
def obtener_carreras():
    conexion = conectar()
    cursor = conexion.cursor(dictionary=True)
    
    cursor.execute('SELECT carrera FROM estudiante GROUP BY carrera')
    carreras = cursor.fetchall()
    
    conexion.close()
    
    return carreras

    
    