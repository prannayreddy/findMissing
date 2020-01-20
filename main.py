import requests
from flask import Flask,render_template,request,redirect,url_for
from werkzeug.utils import secure_filename
import boto3
import pymongo
import dns
import os
import random
import math
from botocore.client import Config
import http.client
from PIL import Image

#Unique AWS Credentials
ACCESS_KEY_ID = "key here"
ACCESS_SECRET_KEY = "Key here"
BUCKET_NAME = 'Bucket name here'

#MongoDb Link
MongoLink="MongoDb Connection link here"



app=Flask(__name__)


@app.route("/home")
def index():
    return render_template('home.html')


# Parent-side Login
@app.route("/parentLogin",methods=["GET","POST"])
def parentLogin():
    if request.method == "POST":
        # Retreive form elements
        pname=request.form["pname"]
        pemail=request.form["pemail"]
        pphone=request.form["pphone"]
        cname=request.form["cname"]
        cage=request.form["cage"]
        cgender=request.form["cgender"]

        # Save uploaded photo temporarily on GCP
        f = request.files['file']
        uploads_dir = os.path.join('//tmp')  
        f.save(os.path.join(uploads_dir, secure_filename(f.filename)))
        
        # Generate random string for unique name
        math.floor(random.random()*1000000000)
        print(uploads_dir)
        print(f.filename)
        print(os.curdir)
        rname=f.filename
        rname1=str( math.floor(random.random()*1000000000))+".jpg"
        os.rename("//tmp/"+rname,"//tmp/"+rname1)

        # Compress image before upload to AWS bucket
        filepath = "//tmp/"+rname1
        oldsize = os.stat(filepath).st_size
        picture = Image.open(filepath)
        dim = picture.size
        picture.save("//tmp/Compressed_"+rname1,"JPEG",optimize=True,quality=10) 
        newsize = os.stat("//tmp/Compressed_"+rname1).st_size
        percent = (oldsize-newsize)/float(oldsize)*100
        print (oldsize)
        print(newsize)
        print(percent)

        # Store the unique image name & child's details in MongoDB
        client1 = pymongo.MongoClient(MongoLink)
        db = client1['FiPo']
        collection=db['LostKids']
        parentInfo={
            "pname":pname,
            "pphone":pphone,
            "pemail":pemail,
            "cname":cname,
            "cgender":cgender,
            "cage":cage,
            "imageid":rname1
        }
        collection.insert_one(parentInfo)

        #S3 Connect & Upload image to Bucket
        FILE_NAME = rname1
        data = open("//tmp/Compressed_"+rname1, 'rb')
        s3 = boto3.resource(
            's3',
            aws_access_key_id=ACCESS_KEY_ID,
            aws_secret_access_key=ACCESS_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        s3.Bucket(BUCKET_NAME).put_object(Key=rname1, Body=data, ACL='public-read')
        print ("Done")

        # Uploading to collection
        collectionId='MyCollection'
        photo=rname1
        client=boto3.client('rekognition', region_name='ap-south-1', aws_access_key_id=ACCESS_KEY_ID, aws_secret_access_key=ACCESS_SECRET_KEY)
        response=client.index_faces(CollectionId=collectionId,
                                    Image={'S3Object':{'Bucket':BUCKET_NAME,'Name':photo}},
                                    ExternalImageId=photo,
                                    MaxFaces=1,
                                    QualityFilter="AUTO",
                                    DetectionAttributes=['ALL'])
        print ('Results for ' + photo) 	
        print('Faces indexed:')						
        for faceRecord in response['FaceRecords']:
                print('  Face ID: ' + faceRecord['Face']['FaceId'])
                print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))
        print('Faces not indexed:')
        for unindexedFace in response['UnindexedFaces']:
            print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
            print(' Reasons:')
            for reason in unindexedFace['Reasons']:
                print('   ' + reason)

        # Cleanup routine       
        data.close()       
        os.remove("//tmp/Compressed_"+rname1)
        return render_template('home.html')
    return render_template('parentLogin.html')


# Reporter-side Login   
@app.route("/userPage",methods=["GET","POST"])
def userPage():
    if request.method == "POST":
        # Retreive form elements
        uname=request.form["uname"]
        uphone=request.form["uphone"]
        ulat=request.form["lat"]
        ulong=request.form["long"]

        # Generate random string for unique name
        f = request.files['file2']  
        uploads_dir = os.path.join('//tmp')  
        f.save(os.path.join(uploads_dir, secure_filename(f.filename)))
        math.floor(random.random()*1000000000)
        print(uploads_dir)
        print(f.filename)
        print(os.curdir)
        rname=f.filename
        rname1=str( math.floor(random.random()*1000000000))+".jpg"
        os.rename("//tmp/"+rname,"//tmp/"+rname1)


        # Compress image before upload to AWS bucket
        filepath = "//tmp/"+rname1
        oldsize = os.stat(filepath).st_size
        picture = Image.open(filepath)
        dim = picture.size
        picture.save("//tmp/Compressed_"+rname1,"JPEG",optimize=True,quality=10) 
        newsize = os.stat("//tmp/Compressed_"+rname1).st_size
        percent = (oldsize-newsize)/float(oldsize)*100
        print (oldsize)
        print(newsize)
        print(percent)


        #S3 Connect & Upload image to Bucket
        FILE_NAME = rname1
        data = open("//tmp/Compressed_"+FILE_NAME, 'rb')
        s3 = boto3.resource(
            's3',
            aws_access_key_id=ACCESS_KEY_ID,
            aws_secret_access_key=ACCESS_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        s3.Bucket(BUCKET_NAME).put_object(Key=FILE_NAME, Body=data, ACL='public-read')
        print ("Done")

        #Searching collections for a match
        bucket='30hacks1'
        collectionId='MyCollection'
        fileName=FILE_NAME
        threshold = 70
        maxFaces=5
        client=boto3.client('rekognition', region_name='ap-south-1', aws_access_key_id=ACCESS_KEY_ID, aws_secret_access_key=ACCESS_SECRET_KEY)
        response=client.search_faces_by_image(CollectionId=collectionId,
                                    Image={'S3Object':{'Bucket':bucket,'Name':fileName}},
                                    FaceMatchThreshold=threshold,
                                    MaxFaces=maxFaces)                           
        faceMatches1=response['FaceMatches']

        #Print matched face indexes
        print ('Matching faces')
        for match in faceMatches1:
            print("Name: "+match['Face']['ExternalImageId'])
            print ('FaceId:' + match['Face']['FaceId'])
            print ('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")

        if faceMatches1:
            # If more than one faces matched, Loop through them
            for faceMatches in faceMatches1:
                print("Entered loop")
                imgid=faceMatches["Face"]["ExternalImageId"]
                imgidpass=imgid
                Similarity=int(faceMatches["Similarity"])
                stringsim=str(Similarity)

                #Find ImageId of matched face in MongoDb & retrieve parents phone no.
                client1 = pymongo.MongoClient(MongoLink)
                db = client1['FiPo']
                collection=db['LostKids']
                parent=collection.find_one({"imageid": imgid})
                pphone=parent['pphone']

                #Fire SMS with Location link
                conn = http.client.HTTPSConnection("api.msg91.com")
                message="Missing Guest found with accuracy: "+stringsim+"% https://www.google.com/maps/search/?api=1&query="+ulat+","+ulong+"    Contact the reporter "+uname+" at "+uphone
                print(type(message))
                print(message)
                payload = '{ "sender": "SOCKET", "route": "4", "country": "91", "sms": [ { "message": "'+message+'", "to": [ "'+pphone+'" ] } ] }'
                headers = {
                'authkey': "Key HERE",
                'content-type': "application/json"
                }
                conn.request("POST", "https://api.msg91.com/api/v2/sendsms?country=91", payload, headers)
                res = conn.getresponse()
                data1 = res.read()
                print(data1.decode("utf-8"))

            #Clean up routine
            data.close()
            os.remove("//tmp/Compressed_"+FILE_NAME)
            return redirect(url_for("results", sim=stringsim, img=imgidpass, img2=rname1)) 

        # IF no face match found
        else:
            #Clean up routine
            print("Nothing")
            data.close()
            os.remove("//tmp/Compressed_"+FILE_NAME)
            return render_template("home.html")
    return render_template('userPage.html')


# Match found Confirmation Page
@app.route("/results",methods=["GET","POST"])
def results():
    #Retrieve Images names uploaded by parent and reporter to display from AWS bucket
    sim=request.args.get('sim',None)
    img=request.args.get('img',None)
    img2=request.args.get('img2',None)
    # These names are used by html page to display image
    return render_template("result.html",sim=sim,img=img,img2=img2)
    
if __name__ == '__main__':
app.run(debug = True)


