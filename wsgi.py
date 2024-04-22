from app import app

if(__name__ == "__main__"):
    app.run(host = "192.168.1.8",debug=True)
    # app.run(threaded=True)
    app.run()