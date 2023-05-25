import pymysql

class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = 3306
    MYSQL_DATABASE = 'Certificados'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = '123456'

    @staticmethod
    def init_app(app):
        pass

    @staticmethod
    def get_db():
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE
        )
        return conn
