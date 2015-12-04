import time
from icalendar import Calendar, Event, vDatetime
from datetime import datetime, timedelta
from flask import Flask, json, request, make_response
from flask_restful import Api, Resource
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists
from caldavHandler import DAVHandler
from flasgger import Swagger

__author__ = 'mfernandes'

DATABASE = 'sqlite:////home/mfernandes/reservationsv5.db'

CALDAV_ADMIN_USER = 'admin-caldav'
CALDAV_ADMIN_PASSWD = 'FZiFFEE1Cc6FXtC8M4bjekrtbqLXyjeM'

app = Flask(__name__)

app.config['SWAGGER'] = {
    "swagger_version": "2.0",
    # headers are optional, the following are default
    # "headers": [
    #     ('Access-Control-Allow-Origin', '*'),
    #     ('Access-Control-Allow-Headers', "Authorization, Content-Type"),
    #     ('Access-Control-Expose-Headers', "Authorization"),
    #     ('Access-Control-Allow-Methods', "GET, POST, PUT, DELETE, OPTIONS"),
    #     ('Access-Control-Allow-Credentials', "true"),
    #     ('Access-Control-Max-Age', 60 * 60 * 24 * 20),
    # ],
    # another optional settings
    # "url_prefix": "swaggerdocs",
    # "subdomain": "docs.mysite,com",
    # specs are also optional if not set /spec is registered exposing all views
    "specs": [
        {
            "version": "0.0.1",
            "title": "Reservation Service",
            "endpoint": 'v1_spec',
            "route": '/v1/spec',
            "description": 'This work implements a generic reservation service. It was developed as part of '
                           'a subject called "service Engineering" in University of Aveiro'

            # rule_filter is optional
            # it is a callable to filter the views to extract

            # "rule_filter": lambda rule: rule.endpoint.startswith(
            #    'should_be_v1_only'
            # )
        }
    ]
}

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE
db = SQLAlchemy(app)

api = Api(app)
Swagger(app)


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

    def get(self):
        """
        Returns a set of all reservations on the service in a JSON format.
        ---
        tags:
            - Reservations API
        responses:
            200:
                description: Array with all reservations made.
                schema:
                    type: object
                    required:
                        - allreservations
                    properties:
                     allreservations:
                          type: object
                          required:
                            - <item_id>
                          properties:
                            <item_id>:
                              type: array
                              items:
                                  type: object
                                  required:
                                    - clienteID
                                    - quantity
                                    - timestamp
                                  properties:
                                    clienteID:
                                      type: integer
                                      description: ID of the client that made the reservation.
                                    quantity:
                                      type: integer
                                      description: Quantity reserved by the user.
                                    timestamp:
                                      type: integer
                                      description: The date for when the reservation is set.
        """
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
        """
        Set a new reservation on the service and returns the ID assigned to that reservations.
        ---
        tags:
            - Reservations API
        parameters:
            - in: body
              name: reservation
              schema:
                type: object
                required:
                  - itemID
                  - quantity
                  - clientID
                  - username
                  - timestamp
                properties:
                  itemID:
                    type: integer
                    description: item ID for identification
                  quantity:
                    type: integer
                    description: quantity to be reserved
                  clientID:
                    type: integer
                    description: ID of the client that wants to make the reservation
                  username:
                    type: string
                    description: username of the user that wants to make the reservation
                  timestamp:
                    type: integer
                    description: the date tha the reservations is scheduled.

        responses:
            200:
              description: Returns the reservation ID that was generated.
              schema:
                type: object
                required:
                    - reservationID
                properties:
                  reservationID:
                    type: integer
                    description: The reservation ID generated
            401:
              description: Invalid itemID
              schema:
                type: string

            402:
              description: Invalid stock
              schema:
                type: string

        """
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
        dh = DAVHandler("http://127.0.0.1:5190/",
                        CALDAV_ADMIN_USER,
                        CALDAV_ADMIN_PASSWD,
                        )
        dh.add_event(reservation.username,
                     reservation.reservationID,
                     stock.itemName,
                     in_data['timestamp'],
                     in_data['quantity'])

        dh.add_event(stock.provider_name,
                     reservation.reservationID,
                     stock.itemName,
                     in_data['timestamp'],
                     in_data['quantity'])

        return {"reservationID": reservation.reservationID}

    def get(self):
        return "400 Invalid Operation"


class UpdateReservation(Resource):

    def post(self, reservation_id):
        """
        Updates the date or the quantity of a reservation with a give reservation ID.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: reservationID
              description: reservation ID of the reservation needs to be updated
              required: true
              type: integer

            - in: body
              name: update parameters
              schema:
                type: object
                required:
                  - quantity
                  - timestamp
                properties:
                  quantity:
                    type: integer
                    description: If the quantity needs to be updates this value must be != 0
                    default: 0
                  timestamp:
                    type: integer
                    description: If the date needs to be updates this value must be != 0
                    default: 0

        responses:
            200:
                description: 200 OK
                schema:
                    type: string
            401:
                description: Invalid parameter value
                schema:
                    type: string

            402:
               description: Reservation ID is not valid
               schema:
                    type: string

            403:
               description: Invalid stock
               schema:
                    type: string
        """
        if database_exists(DATABASE) is False:
            db.create_all()
        in_data = request.get_json(force=True)
        if in_data['quantity'] < 0 or in_data['timestamp'] < 0:
            return "401 Invalid parameter value"
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        if reservation is None:
            return "402 Reservation ID is not valid"
        dh = DAVHandler("http://127.0.0.1:5190/",
                        CALDAV_ADMIN_USER,
                        CALDAV_ADMIN_PASSWD,
                        )
        if in_data['quantity'] > 0:
            stock = Stock.query.filter_by(itemID=reservation.itemID).first()
            if in_data['quantity'] > reservation.quantity:
                more = in_data['quantity'] - reservation.quantity
                if more <= stock.stockQuantity:
                    reservation.quantity = in_data['quantity']
                    stock.stockQuantity -= more
                else:
                    return "403 Invalid stock"
            elif in_data['quantity'] < reservation.quantity:
                less = reservation.quantity - in_data['quantity']
                reservation.quantity = in_data['quantity']
                stock.stockQuantity += less

            dh.update_event(reservation.username,
                            reservation.reservationID,
                            stock.itemName,
                            reservation.timestamp,
                            in_data['quantity'])

            dh.update_event(stock.provider_name,
                            reservation.reservationID,
                            stock.itemName,
                            reservation.timestamp,
                            in_data['quantity'])

        if in_data['timestamp'] > 0:
            reservation.timestamp = in_data['timestamp']
            dh.update_event(reservation.username,
                            reservation.reservationID,
                            stock.itemName,
                            in_data['timestamp'],
                            reservation.quantity)
            dh.update_event(stock.provider_name,
                            stock.itemName,
                            in_data['timestamp'],
                            reservation.quantity)
        db.session.commit()
        return "200 OK"

    def get(self):
        return "400 Invalid Operation"


class CancelReservation(Resource):
    """
        [GET] Deletes a reservation with a given reservation ID.
    """

    def get(self, reservation_id):
        """
        Deletes a reservation with a given reservation ID.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: reservationID
              description: The reservation ID belonging to reservation to be canceled.
              required: true
              type: integer

        responses:
            200:
                description: 200 OK
                schema:
                    type: string

            401:
                description: Reservation ID is not valid
                schema:
                    type: string

        """
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        if reservation is None:
            return "401 Reservation ID is not valid"
        dh = DAVHandler("http://127.0.0.1:5190/",
                        CALDAV_ADMIN_USER,
                        CALDAV_ADMIN_PASSWD,
                        )
        stock = Stock.query.filter_by(itemID=reservation.itemID).first()
        stock.stockQuantity += reservation.quantity
        db.session.delete(reservation)
        db.session.commit()

        dh.delete_event(reservation.username, reservation.reservationID)
        dh.delete_event(stock.provider_name, reservation.reservationID)
        return "200 OK"

    def post(self):
        return "400 Invalid Operation"


class ReplenishStock(Resource):

    def post(self):
        """
        Inserts new stock in the database.
        ---
        tags:
            - Reservations API
        parameters:
            - in: body
              name: All the stock to be inserted
              schema:
                type: object
                required:
                  - info
                  - menu
                properties:
                  info:
                    type: array
                    items:
                        type: object
                        required:
                            - username
                            - providerID
                        properties:
                            username:
                                type: string
                                description: The username of the provider that inserted the stock
                            providerID:
                                type: integer
                                description: The ID of the provider that belongs this stock
                  menu:
                    type: array
                    items:
                      type: object
                      required:
                        - itemID
                        - price
                        - name
                        - quantity
                      properties:
                        itemID:
                            type: integer
                            description: item ID for identification
                        price:
                            type: integer
                            description: the price of the product
                        name:
                            type: string
                            description: the name of the product
                        quantity:
                            type: integer
                            description: The quantity of the product available
        responses:
            200:
                description: 200 OK
                schema:
                    type: string

        """
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
        """
        Returns all the stock available on the service.
        ---
        tags:
            - Reservations API
        responses:
            200:
                description: Returns all the stock available on the service.
                schema:
                    type: object
                    required:
                        - allstock
                    properties:
                        allstock:
                            type: array
                            items:
                                type: object
                                required:
                                    - itemID
                                    - itemName
                                    - itemQuantity
                                properties:
                                    itemID:
                                      type: integer
                                      description: The id of the stock
                                    itemName:
                                      type: string
                                      description: The name of the product in stock
                                    itemQuantity:
                                      type: integer
                                      description: The quantity available for reservation
        """
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
        """
        Returns all the reservations made by a specific user.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: username
              description: The username of the user to list his reservations
              required: true
              type: string
        responses:
            200:
                description: Returns all the reservations made by user with the given username.
                schema:
                    type: object
                    required:
                        - reservations
                    properties:
                        reservations:
                            type: array
                            items:
                                type: object
                                required:
                                    - reservationID
                                    - providerID
                                    - itemID
                                    - itemName
                                    - timestamp
                                    - quantity
                                properties:
                                    reservationID:
                                        type: integer
                                        description: The ID of the reservation made by the user
                                    providerID:
                                        type: integer
                                        description: The ID of the provider that will attend the request made by the user
                                    itemID:
                                        type: integer
                                        description: The ID of the product in stock that was reserved
                                    itemName:
                                        type: string
                                        description: The name of the item reserved
                                    timestamp:
                                        type: integer
                                        description: The date for when the reservation is made
                                    quantity:
                                        type: integer
                                        description: The quantity reserved for this item
        """
        if database_exists(DATABASE) is False:
            db.create_all()
        l2 = []
        for r, s in db.session.query(Reservations, Stock).filter(Stock.itemID == Reservations.itemID,
                                                                 Reservations.username == username).all():
            l2.append({'reservationID': r.reservationID,
                       'providerID': s.providerID,
                       'itemID': r.itemID,
                       'itemName': s.itemName,
                       'timestamp': r.timestamp,
                       'quantity': r.quantity})
        return {"reservations": l2}

    def post(self):
        return "400 Invalid Operation"


class ProviderStock(Resource):

    def get(self, provider_id):
        """
        Returns all the stock available from one provider.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: provider_id
              description: The ID of the provider to list all the available stock
              required: true
              type: integer
        responses:
            200:
                description: Returns all the current stock for the items belonging to a specific provider
                schema:
                    type: object
                    required:
                        - stock
                    properties:
                        allstock:
                            type: array
                            items:
                                type: object
                                required:
                                    - itemID
                                    - itemName
                                    - itemQuantity
                                properties:
                                    itemID:
                                        type: integer
                                        description: The ID of the product in stock belonging to the provider ID received
                                    itemName:
                                        type: string
                                        description: The item name
                                    itemQuantity:
                                        type: integer
                                        description: The item quantity available in the system
        """
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
        """
        Returns all the future reservations related to a particular provider.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: provider_id
              description: The ID of the provider to list all the item currently reserved
              required: true
              type: integer
        responses:
            200:
                description: Returns a list with all the items reserved form now until the future for the given provider ID
                schema:
                    type: object
                    required:
                        - reservated
                    properties:
                        reservated:
                            type: array
                            items:
                                type: object
                                required:
                                    - itemID
                                    - itemName
                                    - quantity
                                properties:
                                    itemID:
                                        type: integer
                                        description: The ID of the product in stock belonging to the provider ID received
                                    itemName:
                                        type: string
                                        description: The item name
                                    quantity:
                                        type: integer
                                        description: The reserved quantity
        """
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

    def get(self, provider_id):
        """
        Returns the total reservation that one provider has in the future.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: provider_id
              description: The ID of the provider to get the sum o all reserved stock
              required: true
              type: integer
        responses:
            200:
                description: Returns the sum of all the stock reserved
                schema:
                    type: object
                    required:
                        - reservated
                    properties:
                        reservated:
                            type: array
                            items:
                                type: object
                                required:
                                    - total
                                properties:
                                    total:
                                        type: integer
                                        description: The total of rthe stock of the provider reserved
        """
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

    def post(self, provider_id):
        """
        Returns all the reservations from one provider for one specific day.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: provider_id
              description: The ID of the provider
              required: true
              type: integer
            - in: body
              name: All the stock to be inserted
              schema:
                type: object
                required:
                    - date
                properties:
                    date:
                        type: string
                        description: The date for the day to list the reserves
                        default: 'dd/mm/yy'
        responses:
            200:
                description: Returns all the reservations for the given provider ID for a specific day
                schema:
                    type: object
                    required:
                        - reservated
                    properties:
                        reservated:
                            type: array
                            items:
                                type: object
                                required:
                                    - itemID
                                    - reservations
                                properties:
                                    itemID:
                                        type: integer
                                        description: The item ID of the item
                                    reservations:
                                        type: array
                                        items:
                                            type: object
                                            required:
                                                - quantity
                                                - timestamp
                                                - username
                                            properties:
                                                quantity:
                                                    type: integer
                                                    description: The quantity reserved by the user
                                                timestamp:
                                                    type: integer
                                                    description: The date for when the reservation was made
                                                username:
                                                    type: string
                                                    description: The username of the user that made the reservation
        """
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
        """
        Returns a file related to a reservation in iCal format.
        ---
        tags:
            - Reservations API
        parameters:
            - in: path
              name: reservation_id
              description: The ID of the reservation to get the iCla file
              required: true
              type: integer
        response:
            200:
                description: Returns a iCal file
                type: String
            401:
                description: Invalid reservation ID
                type: string
        """
        if database_exists(DATABASE) is False:
            db.create_all()
        reservation = Reservations.query.filter_by(reservationID=reservation_id).first()
        if reservation is None:
            return '401 Invalid reservation ID'
        stock = Stock.query.filter_by(itemID=reservation.itemID).first()

        cal = Calendar()
        cal['version'] = "2.0"
        cal['prodid'] = "//Radicale//NONSGML Radicale Server//EN"
        event = Event()
        event['uid'] = reservation.reservationID
        event['dtstart'] = vDatetime(datetime.fromtimestamp(reservation.timestamp)).to_ical()
        event['summary'] = stock.itemName
        event['description'] = 'Quantity: ' + str(reservation.quantity)
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
