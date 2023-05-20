import pyodbc

class Config:
    SQL_SERVER = '34.123.86.131'
    SQL_DATABASE = 'Certificados'
    SQL_USERNAME = 'ConexionCertificados'
    SQL_PASSWORD = 'ConexionCertificados'
    SQL_DRIVER = 'ODBC Driver 17 for SQL Server'

    @staticmethod
    def init_app(app):
        pass

def get_db():
    conn_str = f"DRIVER={Config.SQL_DRIVER};SERVER={Config.SQL_SERVER};DATABASE={Config.SQL_DATABASE};UID={Config.SQL_USERNAME};PWD={Config.SQL_PASSWORD}"
    return pyodbc.connect(conn_str)