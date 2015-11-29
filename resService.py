import time
from icalendar import Calendar, Event, vDatetime
from datetime import datetime, timedelta
from flask import Flask, json, request, make_response
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
    """
        Defines the database table using SQLAlchemy for storing the reservations.
    """
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
    """
        Defines the database table using SQLAlchemy for storing the stock available.
    """
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
    """
        [GET] Returns a set of all reservations on the service in a JSON format.
        JSON sent:
        {
            "allreservations": {
                "0": [
                    {
                        "clientID": 9,
                        "quantity": 3,
                        "timestamp": 1448733600
                    }
                ],
                "1": [
                    {
                        "clientID": 9,
                        "quantity": 1,
                        "timestamp": 1448913600
                    }
                ]
            }
        }
    """

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
    """
        [POST] Set a new reservation on the service and returns the ID assigned to that reservations.
        JSON received:
        {
            "itemID": 8,
            "quantity": 2,
            "clientID": 12,
            "username": "dave1",
            "timestamp": 1445556339
        }
    """

    def post(self):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        stock = Stock.query.filter_by(itemID=in_data['itemID']).first()
        if stock is None:
            return "401 Invalid itemID"
        if stock.stockQuantity < in_data['quantity']:
            return "402 Invalid stock"
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

        return {"reservationID": reservation.reservationID}

    def get(self):
        return "400 Invalid Operation"


class UpdateReservation(Resource):
    """
        [POST] Updates the info related to a reservation. Only updates the parameters received that is nonzero.
        JSON received:
        {
            "quantity": 2,
            "timestamp": 1445556339
        }
    """
    def post(self, reservation_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        if in_data['quantity'] < 0 or in_data['timestamp'] < 0:
            return "401 Invalid parameter value"
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        if reservation is None:
            return "402 Reservation ID is not valid"
        if in_data['quantity'] > 0:
            stock = Stock.query.filter_by(itemID=reservation.itemID).first()
            if in_data['quantity'] > reservation.quantity:
                more = in_data['quantity'] - reservation.quantity
                if more <= stock.stockQuantity:
                    reservation.quantity += more
                    stock.stockQuantity -= more
                else:
                    return "403 Invalid stock"
            elif in_data['quantity'] < reservation.quantity:
                less = reservation.quantity - in_data['quantity']
                reservation.quantity -= less
                stock.stockQuantity += less

        if in_data['timestamp'] > 0:
            reservation.timestamp = in_data['timestamp']
        db.session.commit()
        return "200 OK"

    def get(self):
        return "400 Invalid Operation"


class CancelReservation(Resource):
    """
        [GET] Deletes a reservation with a given reservation ID.
    """
    def get(self, reservation_id):
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        if reservation is None:
            return "401 Reservation ID is not valid"
        stock = Stock.query.filter_by(itemID=reservation.itemID).first()
        stock.stockQuantity += reservation.quantity
        db.session.delete(reservation)
        db.session.commit()
        return "200 OK"

    def post(self):
        return "400 Invalid Operation"


class ReplenishStock(Resource):
    """
        [POST] Inserts new stock in the database.
        JSON received:
        {
            "info": [
                {
                    "username": "dave1",
                    "providerID": 1
                }
            ],
            "menu": [
                {
                    "itemID": 8,
                    "price": 10,
                    "name": "peixe",
                    "quantity": 20
                },
                {
                    "itemID": 9,
                    "price": 10,
                    "name": "carne",
                    "quantity": 20
                }
            ]
        }
    """

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
    """
        [GET] Returns all the stock available on the service.
        JSON sent:
        {
            "allstock": [
                {
                    "itemID": 0,
                    "itemName": "pratodeteste",
                    "itemQuantity": 12
                },
                {
                    "itemID": 1,
                    "itemName": "pratodeteste222",
                    "itemQuantity": 17
                }
            ]
        }
    """

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
    """
        [GET] Returns all the reservations made by a specific user.
        JSON sent:
        {
            "reservations": [
                {
                    "itemID": 8,
                    "itemName": "peixe",
                    "timestamp": 123452356343,
                    "provider": "dave1",
                    "quantity": 2
                },
                {
                    "itemID": 8,
                    "itemName": "peixe",
                    "timestamp": 123452356343,
                    "provider": "dave1",
                    "quantity": 2
                }
            ]
        }
    """

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
    """
        [GET] Returns all the stock available from one provider.
        JSON sent:
        {
            "stock": [
                {
                    "itemID": 8,
                    "itemName": "peixe",
                    "itemQuantity": 18
                },
                {
                    "itemID": 9,
                    "itemName": "carne",
                    "itemQuantity": 20
                }
            ]
        }
    """

    def get(self, provider_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        l2 = []
        stock = Stock.query.filter_by(providerID=provider_id).all()
        l = [a.to_json() for a in stock]
        for item in l:
            l2.append({'itemID': item['itemID'], 'itemName': item['itemName'], 'itemQuantity': item['stockQuantity']})
        return {"stock": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderReservated(Resource):
    """
        [GET] Returns all the future reservations related to a particular provider.
        JSON sent:
        {
            "reservated": [
                {
                    "itemID": 9,
                    "itemName": "carne",
                    "quantity": 2
                }
            ]
        }
    """

    def get(self, provider_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        stock_provider = Stock.query.filter_by(providerID=provider_id).all()
        l2 = []
        timestamp_now = int(time.time())
        for item in stock_provider:
            reserv = Reservations.query.filter_by(itemID=item.itemID).all()
            if len(reserv) != 0:
                count = 0
                for item2 in reserv:
                    if item2.timestamp > timestamp_now:
                        count += item2.quantity
                l2.append({'itemID': item.itemID, 'itemName': item.itemName, 'quantity': count})
        return {"reservated": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderReservatedTF(Resource):
    """
        [GET] Returns the total reservation that one provider has in the future.
        JSON sent:
        {
            "reservated": [
                {
                    "total": 0
                }
            ]
        }
    """

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
    """
        [POST] Returns all the reservations from one provider for one specific day.
        JSON received:
        {
            "date": "26/11/2015"
        }

        JSON sent:
        {
            "reservated" : [
            {
                "itemID": 1,
                "reservations" : [
                    {
                        "itemID": 0,
                        "itemName": "dsf",
                        "quantity": 2,
                        "timestamp": 123342512343,
                        "username": "mmf"
                    },
                    {
                        "itemID": 0,
                        "itemName": "dsf",
                        "quantity": 2,
                        "timestamp": 12334251233,
                        "username": "mmf"
                    }
                ]
            },
            {
                "itemID": 2,
                "reservations" : [
                    {
                        "itemID": 0,
                        "itemName": "dsf",
                        "quantity": 2,
                        "timestamp": 123342512343,
                        "username": "mmf"
                    },
                    {
                        "itemID": 0,
                        "itemName": "dsf",
                        "quantity": 2,
                        "timestamp": 12334251233,
                        "username": "mmf"
                    }
                ]
            }

            ]
        }
    """

    def post(self, provider_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        stock_provider = Stock.query.filter_by(providerID=provider_id).all()
        l2 = []
        dater = datetime.strptime(in_data['date'], "%d/%m/%Y")
        timestamp_begin = int(time.mktime(dater.timetuple()))
        timestamp_end = int(time.mktime((dater + timedelta(1)).timetuple()))
        for item in stock_provider:
            reserv = Reservations.query.filter_by(itemID=item.itemID).all()
            if len(reserv) != 0:
                l3 = []
                for item2 in reserv:
                    if (item2.timestamp > timestamp_begin) and (item2.timestamp < timestamp_end):
                        l3.append({'quantity': item2.quantity,
                                   'timestamp': item2.timestamp,
                                   'username': item2.username})
                if len(l3) != 0:
                    l2.append({'itemID': item.itemID, 'itemName': item.itemName, 'reservations': l3})
        return {"reservated": l2}

    def get(self):
        return "400 Invalid Operation"


class GetCaldavFile(Resource):
    """
        [GET] Returns a file related to a reservation in iCal format.
    """

    def get(self, reservation_id):
        if database_exists(DATABASE) is False:
            db.create_all()
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        stock = Stock.query.filter_by(itemID=reservation.itemID).first()

        cal = Calendar()
        cal['version'] = "2.0"
        cal['prodid'] = "//Radicale//NONSGML Radicale Server//EN"
        event = Event()
        event['uid'] = reservation.reservationID
        event['dtstart'] = vDatetime(datetime.fromtimestamp(reservation.timestamp)).to_ical()
        event['summary'] = stock.itemName
        event['x-radicale-name'] = str(reservation.reservationID) + '.ics'
        cal.add_component(event)

        response = make_response(cal.to_ical())
        response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
        return response


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
            return "401 Database doesn't exist"
        db.drop_all()
        db.create_all()
        return "200 OK"


api.add_resource(AllReservations, '/allreservations')
api.add_resource(DoReservation, '/doreservation')
api.add_resource(UpdateReservation, '/updatereserv/<reservation_id>')
api.add_resource(CancelReservation, '/cancelreserv/<reservation_id>')
api.add_resource(ReplenishStock, '/replenishstock')
api.add_resource(AllStock, '/allstock')
api.add_resource(UserReservations, '/userresv/<username>')
api.add_resource(ProviderStock, '/providerstock/<provider_id>')
api.add_resource(ProviderReservated, '/reservationsnumber/<provider_id>')
api.add_resource(ProviderReservatedTF, '/reservtotal/<provider_id>')
api.add_resource(ProviderReservatedTFDay, '/dayreserv/<provider_id>')
api.add_resource(GetCaldavFile, '/getfile/<reservation_id>')
api.add_resource(CheckStock, '/stock/<item_id>')
api.add_resource(ResetDatabase, '/resetdb')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
