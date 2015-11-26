import time
from datetime import datetime, timedelta
from flask import Flask, json, request
from flask_restful import Api, Resource
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists
from caldavHandler import DAVHandler

__author__ = 'mfernandes'

DATABASE = 'sqlite:////home/mfernandes/reservationsv5.db'

CALDAV_ADMIN_USER = 'admin-caldav'
CALDAV_ADMIN_PASSWD = 'FZiFFEE1Cc6FXtC8M4bjekrtbqLXyjeM'

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
db = SQLAlchemy(app)

api = Api(app)


# ------------------------------------------------  Database definition  ---------------------------------------------


class Reservations(db.Model):
    __tablename__ = "reservations"
    reservationID = db.Column(db.Integer, primary_key=True)
    itemID = db.Column(db.Integer, db.ForeignKey('stock.itemID'))
    quantity = db.Column(db.Integer)
    timestamp = db.Column(db.BigInteger)
    clientID = db.Column(db.Integer)
    username = db.Column(db.Integer)
    binary_data = db.Column(db.LargeBinary)

    def __init__(self, itemID, quantity, clientID, username, timestamp=None, binary_data=None):
        self.itemID = itemID
        self.quantity = quantity
        if timestamp is None:
            self.timestamp = int(time.time())
        self.timestamp = timestamp
        self.clientID = clientID
        self.username = username
        self.binary_data = binary_data

    def to_json(self):
        return dict(reservationID=self.reservationID, itemID=self.itemID, quantity=self.quantity,
                    timestamp=self.timestamp, clientID=self.clientID, username=self.username)


class Stock(db.Model):
    __tablename__ = "stock"
    itemID = db.Column(db.Integer, primary_key=True)
    providerID = db.Column(db.Integer)
    provider_name = db.Column(db.String(20))
    itemName = db.Column(db.String(20))
    price = db.Column(db.Integer)
    stockQuantity = db.Column(db.Integer)

    def __init__(self, providerID, provider_name, itemID, itemName, price, stockQuantity):
        self.providerID = providerID
        self.provider_name = provider_name
        self.itemName = itemName
        self.itemID = itemID
        self.price = price
        self.stockQuantity = stockQuantity

    def to_json(self):
        return dict(itemID=self.itemID, providerID=self.providerID,
                    provider_name=self.provider_name,
                    itemName=self.itemName,
                    price=self.price,
                    stockQuantity=self.stockQuantity)


# -------------------------------------------------------------------------------------------------------------------


class AllReservations(Resource):
    def get(self):
        if database_exists(DATABASE) is False:
            db.create_all()
        all_reser = Reservations.query.all()
        l = [a.to_json() for a in all_reser]
        res = dict()
        for item in l:
            item_id = item.get('itemID')
            if str(item_id) not in res:
                res[str(item_id)] = list()
            res[str(item_id)].append({'clientID': item['clientID'],
                                      'quantity': item['quantity'], 'timestamp': item['timestamp']})
        return json.dumps({'allreservations': res})

    def post(self):
        return "400 Invalid Operation"


class DoReservation(Resource):
    def post(self):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        stock = Stock.query.filter_by(itemID=in_data['itemID']).first()
        if stock is None:
            return "401 Invalid itemID"
        if stock.stockQuantity < in_data['quantity']:
            return "402 Available stock is less than the requested value"
        res = Reservations(stock.itemID,
                           in_data['quantity'],
                           in_data['clientID'],
                           in_data['username'],
                           in_data['timestamp'])

        db.session.add(res)
        stock.stockQuantity -= in_data['quantity']
        db.session.commit()

        reservation = Reservations.query.filter_by(itemID=stock.itemID, clientID=in_data['clientID']).first()
        dh = DAVHandler("http://127.0.0.1:5190/%s/meals.ics/" % in_data['username'],
                        CALDAV_ADMIN_USER,
                        CALDAV_ADMIN_PASSWD,
                        )
        dh.add_event(reservation.reservationID, stock.itemName, in_data['timestamp'])

        dh = DAVHandler("http://127.0.0.1:5190/%s/meals.ics/" % stock.provider_name,
                        CALDAV_ADMIN_USER,
                        CALDAV_ADMIN_PASSWD,
                        )
        dh.add_event(reservation.reservationID, stock.itemName, in_data['timestamp'])

        return "200 OK"

    def get(self):
        return "400 Invalid Operation"


class ReplenishStock(Resource):
    def post(self):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        provider_id = in_data['info'][0]['providerID']
        provider_name = in_data['info'][0]['username']
        for item in in_data['menu']:
            stock = Stock.query.filter_by(itemID=item['itemID']).first()
            if stock is not None:
                stock.stockQuantity += item['quantity']
            else:
                new_stock = Stock(provider_id,
                                  provider_name,
                                  item['itemID'],
                                  item['name'],
                                  item['price'],
                                  item['quantity'])
                db.session.add(new_stock)
            db.session.commit()
        return "200 OK"

    def get(self):
        return "400 Invalid Operation"


class AllStock(Resource):
    def get(self):
        if database_exists(DATABASE) is False:
            db.create_all()
        all_stock = Stock.query.all()
        l = [a.to_json() for a in all_stock]
        l2 = []
        for item in l:
            l2.append({'itemID': item['itemID'], 'itemName': item['itemName'], 'itemQuantity': item['stockQuantity']})
        return {"allstock": l2}

    def post(self):
        return "400 Invalid Operation"


class UserReservations(Resource):
    def get(self, username):
        if database_exists(DATABASE) is False:
            db.create_all()
        l2 = []
        for r, s in db.session.query(Reservations, Stock).filter(Stock.itemID == Reservations.itemID).all():
            l2.append({'itemID': r.itemID,
                       'itemName': s.itemName,
                       'timestamp': r.timestamp,
                       'provider': s.provider_name,
                       'quantity': r.quantity})
        return {"reservations": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderStock(Resource):
    def get(self, provider_name):
        if database_exists(DATABASE) is False:
            db.create_all()
        l2 = []
        stock = Stock.query.filter_by(provider_name=provider_name).all()
        l = [a.to_json() for a in stock]
        for item in l:
            l2.append({'itemID': item['itemID'], 'itemName': item['itemName'], 'itemQuantity': item['stockQuantity']})
        return {"stock": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderReservated(Resource):
    def get(self, provider_name):
        if database_exists(DATABASE) is False:
            db.create_all()
        stock_provider = Stock.query.filter_by(provider_name=provider_name).all()
        l2 = []
        for item in stock_provider:
            reserv = Reservations.query.filter_by(itemID=item.itemID).all()
            if len(reserv) != 0:
                count = 0
                for item2 in reserv:
                    count += item2.quantity
                l2.append({'itemID': item.itemID, 'itemName': item.itemName, 'quantity': count})
        return {"reservated": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderReservatedTF(Resource):
    def get(self, provider_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        stock_provider = Stock.query.filter_by(providerID=provider_id).all()
        timestamp_now = int(time.time())
        for item in stock_provider:
            reserv = Reservations.query.filter_by(itemID=item.itemID).all()
            count = 0
            if len(reserv) != 0:
                for item2 in reserv:
                    if item2.timestamp > timestamp_now:
                        count += 1
        return {"reservated": [{'total': count}]}

    def post(self):
        return "400 Invalid Operation"


class ProviderReservatedTFDay(Resource):
    def get(self, provider_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        stock_provider = Stock.query.filter_by(providerID=provider_id).all()
        l2 = []
        dater = datetime.datetime.strptime(in_data['date'], "%d/%m/%Y")
        timestamp_begin = int(time.mktime(dater.timetuple()))
        timestamp_end = int(time.mktime((dater + datetime.timedelta(1)).timetuple()))
        for item in stock_provider:
            reserv = Reservations.query.filter_by(itemID=item.itemID).all()
            if len(reserv) != 0:
                for item2 in reserv:
                    if (item2.timestamp > timestamp_begin) and (item2.timestamp < timestamp_end):
                        l2.append({'itemID': item.itemID, 'itemName': item.itemName, 'quantity': item2.quantity,
                                   'username': item2.username})
        return {"reservated": l2}

    def post(self):
        return "400 Invalid Operation"


class GetCaldavFile(Resource):
    def get(self, reservation_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        return json.dumps(
            {'url': 'http://ogaviao.ddns.net/%s/meals.ics/%d.ics' % (reservation.username, reservation_id)})


class CheckStock(Resource):
    def get(self, item_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        stock = Stock.query.filter_by(itemID=item_id).first()
        json = stock.to_json()
        return {'itemID': json['itemID'], 'stockQuantity': json['stockQuantity']}

    def post(self):
        return "400 Invalid Operation"


class ResetDatabase(Resource):
    def get(self):
        if database_exists(DATABASE) is False:
            return "406 Database doesn't exist!"
        db.drop_all()
        db.create_all()
        return "200 OK"


api.add_resource(AllReservations, '/allreservations')
api.add_resource(DoReservation, '/doreservation')
api.add_resource(ReplenishStock, '/replenishstock')
api.add_resource(AllStock, '/allstock')
api.add_resource(UserReservations, '/userresv/<username>')
api.add_resource(ProviderStock, '/providerstock/<provider_name>')
api.add_resource(ProviderReservated, '/reservationsnumber/<provider_name>')
api.add_resource(ProviderReservatedTF, '/reservtotal/<provider_id>')
api.add_resource(ProviderReservatedTFDay, '/dayreserv/<provider_id>')
api.add_resource(GetCaldavFile, '/getfile/<reservation_id>')
api.add_resource(CheckStock, '/stock/<item_id>')
api.add_resource(ResetDatabase, '/resetdb')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
