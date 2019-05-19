import psycopg2

class DatabaseCon:
    def __init__(self):
        self.conn = psycopg2.connect("dbname='database_name' user='username' ' password='dbpassword'")
        self.cur = self.conn.cursor()

    def queryIfExist(self, query):
        self.cur.execute(query)
        if self.cur.fetchone() is None:
            return False
        else:
            return True
    
    def query(self, query):
        self.cur.execute(query)
        self.conn.commit()
        

    def selectAll(self, query):
        self.cur.execute(query)
        return self.cur.fetchall()
    
    def SelectOne(self, query):
        self.cur.execute(query)
        return self.cur.fetchone()

    def close(self):
        self.cur.close()
        self.conn.close()
