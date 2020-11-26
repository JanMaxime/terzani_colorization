from flask import Flask, redirect, url_for, render_template, request, jsonify
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
import os
import json
from dotenv import load_dotenv
load_dotenv()

from search import *

app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
mongo = PyMongo(app)
sample_annotations = mongo.db["sample_annotations"]
sample_tags = mongo.db["sample_taggings"]


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
	return render_template("home.html")

@app.route("/gallery", methods=["GET", "POST"])
def gallery():
	iiifs_and_links = []
	if request.method == "POST":
		display_markers = request.form.get("display_markers", False)
		if display_markers:
			results = get_markers(sample_annotations)
			lat_lng_name = [result["annotation"]["landmark_info"] for result in results]
			return jsonify({"lat_lng_name" : lat_lng_name})
		else:
			results = search_country(request.form["country"], sample_annotations)
			iiifs_and_links = [(json.dumps(result["annotation"]["iiif"]), result["annotation"]["iiif"]["images"][0]["resource"]["service"]["@id"][:-4] + "/full/,360/0/default.jpg") for result in results]
			return jsonify({"data" : render_template("display_images.html", iiifs_and_links=iiifs_and_links)})

	return render_template("gallery.html")


@app.route("/search", methods=["GET", "POST"])
def search_page():
	iiif_and_links = []
	number_of_results = 0
	display_bb = False
	item = ""
	if request.method == "POST":
		if request.form["submit"] == "text_search":
			item = request.form["item"]
			display_bb = request.form.get("display_bb", False)
			photos, searched_items = search_photos(item, sample_tags, sample_annotations)

			if not display_bb:
				for res_photo in photos:
					photo = res_photo["annotation"]
					new_item = (json.dumps(photo["iiif"]), [photo["iiif"]["images"][0]["resource"]["service"]["@id"][:-4] + "/full/,360/0/default.jpg"])
					number_of_results += len(new_item[1])
					iiif_and_links.append(new_item)
			else:
				for res_photo in photos:
					photo = res_photo["annotation"]
					for sitem in searched_items:
						box_key = next( (key for key in photo["obj_boxes"] if sitem in key), None )
						if box_key:
							new_item = (json.dumps(photo["iiif"]), [photo["iiif"]["images"][0]["resource"]["service"]["@id"][:-4] + "/" + str (box[0]) + "," + str (box[1]) + "," +str (box[2]) + "," + str (box[3]) + "/max/0/default.jpg" for box in photo["obj_boxes"][box_key]])
							number_of_results += len(new_item[1])
							iiif_and_links.append(new_item)
		elif request.form["submit"] == "image_search":
			image_file = request.files["image_file"]
			if image_file and allowed_file(image_file.filename):
				#TODO: replace these lines that save the uploaded pictures with the code to colorize the image
				filename = secure_filename(image_file.filename)
				image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		
	return render_template("search.html", results = iiif_and_links, number_of_results=number_of_results, display_bb = display_bb, item=item, cold_start = request.method == "GET")


if __name__ == "__main__":
	app.run(debug=True)
