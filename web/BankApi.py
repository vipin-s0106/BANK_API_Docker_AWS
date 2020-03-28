from flask import Flask,request,jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import datetime

app = Flask(__name__)
api = Api(app)

#************************** Mongo DB Implementation ************

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client.BankDB
accounts = db["Accounts"]
users = db["Users"]

#****************************************************************


def UserExist(username):
    if db.users.count({'username':username}) == 0:
        return False
    return True

def verify_pw(username,password):
    pwd = db.users.find({'username':username})[0]['password']
    if bcrypt.checkpw(password.encode('utf8'),pwd):
        return True
    return False

def verify_credentials(username,password):
    if UserExist(username) and verify_pw(username,password):
        return True
    return False

def generateJsonResponse(status,msg):
    return {
        "status_code":status,
        "msg":msg
    }

def getUserBalance(username):
    bal = db.users.find({'username':username})[0]['account']['balance']
    return bal

def getUserDebt(username):
    debt = db.users.find({'username':username})[0]['account']['debt']
    return debt


def getUserBankDetails(username,password):
    if verify_credentials(username,password):
        account_details = db.users.find({'username':username})[0]['account']
        return account_details,True
    return generateJsonResponse(301,"Invalid Username/Password"),False


class Register(Resource):
    def post(self):
        postedData = request.get_json()

        if "username" in postedData and "password" in postedData:
            username = postedData['username']
            password = postedData['password']

            if not UserExist(username):
                count = db.users.count()
                account_id = datetime.datetime.now().strftime("%Y%m%d")+str(count+1)
                db.accounts.insert({
                    "account_no":account_id,
                    "balance":0,
                    "debt":0
                })
                account = db.accounts.find({"account_no":account_id})[0]
                hash_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())
                db.users.insert({
                    'username':username,
                    'password':hash_pw,
                    'account':account
                })

                retJson = {
                    'status_code':200,
                    'msg':"User has been successfully registered"
                }
                return jsonify(retJson)

            return jsonify(generateJsonResponse(302,"User has already registered with the bank"))
        return jsonify(generateJsonResponse(301,"Invalid Username/Password input"))

class Add(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        amount = postedData['amount']


        if verify_credentials(username,password):
            bal= getUserBalance(username)
            if amount > 0:
                db.users.update({
                    'username':username
                },{
                    '$set':{
                        'account.balance': bal+amount
                    }
                }
                )

                return jsonify(generateJsonResponse(200,"Balance Added successfully"))
            return  jsonify(generateJsonResponse(302,"Invalid balance to add"))

        return jsonify(generateJsonResponse(301,"Invalid Username/Password"))


class Transfer(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        to_username = postedData['to_username']
        amount = postedData['amount']

        if not UserExist(to_username):
            return  jsonify(generateJsonResponse(302,"Invalid recipient account"))
        if verify_credentials(username,password):
            from_balance = getUserBalance(username)
            to_balance = getUserBalance(to_username)
            if from_balance >= amount:
                db.users.update({
                    'username': to_username}, {
                    '$set': {
                        'account.balance'
                            : to_balance + amount

                    }
                }
                )
                db.users.update({
                    'username': username}, {
                    '$set': {
                        'account.balance':
                            from_balance - amount

                    }
                }
                )
                return jsonify(generateJsonResponse(200,"Balance Transfered successfully"))
            return jsonify(generateJsonResponse(303,"Insufficient Balance"))
        return jsonify(generateJsonResponse(301,"Invalid Username/Password"))

class GetLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        amount = postedData['amount']


        if verify_credentials(username,password):
            bal = getUserBalance(username)
            if amount > 0:
                db.users.update({
                    'username':username},{
                        '$set':{
                            'account.balance':bal+amount,
                            'account.debt':amount
                        }
                    }
                )
                return jsonify(generateJsonResponse(200,"Loan successfully received"))
            return  jsonify(generateJsonResponse(302,"Invalid balance for debt"))

        return jsonify(generateJsonResponse(301,"Invalid Username/Password"))

class ReturnLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        amount = postedData['amount']


        if verify_credentials(username,password):
            bal = getUserBalance(username)
            debt = getUserDebt(username)
            if amount <= debt and bal >= debt:
                db.users.update({
                    'username':username},{
                        '$set':{
                            'account.balance':bal-amount,
                            'account.debt':debt-amount
                        }
                    }
                )
                return jsonify(generateJsonResponse(200,"Loan returned successfully"))
            return  jsonify(generateJsonResponse(302,"Invalid debt amount to return the loan"))

        return jsonify(generateJsonResponse(301,"Invalid Username/Password"))

class GetAccountDetail(Resource):
    def get(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']

        result,status = getUserBankDetails(username,password)
        if status:
            del result['_id']
            msg = {'bank_detail':result}
            msg['status_code'] = 200
            return jsonify(msg)
        return jsonify(result)

api.add_resource(Register,'/register')
api.add_resource(Add,'/add')
api.add_resource(Transfer,'/transfer')
api.add_resource(GetLoan,'/getloan')
api.add_resource(ReturnLoan,'/returnloan')
api.add_resource(GetAccountDetail,'/getaccount')

if __name__ == "__main__":
    app.run(debug=True)
