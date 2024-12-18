# importing the necessary dependencies
from flask import Flask, render_template, request, send_file
from flask_cors import CORS, cross_origin
import numpy as np
import os
import tensorflow as tf
import easyocr as ocr
import cv2
from object_detection.utils import label_map_util

os.putenv('LANG', 'en_US.UTF-8')
os.putenv('LC_ALL', 'en_US.UTF-8')

app = Flask(__name__)  # initializing a flask app
CORS(app)

MODEL_NAME = 'auto_no_plate_detection_model'

# Path to frozen detection graph. This is the actually  model that is used for object detection.
PATH_TO_FROZEN_GRAPH = MODEL_NAME + '/frozen_inference_graph.pb'

# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join('training', 'classes.pbtxt')

# Disable eager execution (needed for TensorFlow 1.x style graph execution)
tf.compat.v1.disable_eager_execution()

# loading tf graph
detection_graph = tf.compat.v1.Graph()
with detection_graph.as_default():
    od_graph_def = tf.compat.v1.GraphDef()
    with tf.io.gfile.GFile(PATH_TO_FROZEN_GRAPH, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

# loading classes file
category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS, use_display_name=True)

# run reader object of OCR
reader = ocr.Reader(['en'])

# States of India
states = {
    "AN": "Andaman and Nicobar", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CH": "Chandigarh", "DN": "Dadra and Nagar Haveli", "DD": "Daman and Diu", "DL": "Delhi", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir", "KA": "Karnataka", "KL": "Kerala", "LD": "Lakshadweep",
    "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha",
    "PY": "Pondicherry", "PN": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TR": "Tripura", "UP": "Uttar Pradesh",
    "WB": "West Bengal", "CG": "Chhattisgarh", "TS": "Telangana", "JH": "Jharkhand", "UK": "Uttarakhand"
}


@app.route('/', methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    return render_template("index.html")


@app.route('/startapp', methods=['POST', 'GET'])  # route to show the predictions in a web UI
@cross_origin()
def upload_img():
    if request.method == 'POST':
        return render_template('upload.html')
    else:
        return "something went wrong"


@app.route('/detection', methods=['POST', 'GET'])  # route to show the predictions in a web UI
@cross_origin()
def detection():
    if request.method == 'POST':
        try:
            # reading image file
            uploaded_file = request.files['upload_file']
            filename = uploaded_file.filename

            # proceed only if file is available
            if uploaded_file.filename != '':
                uploaded_file.save(filename)

                # proceed only if image is in "jpg,jpeg,png" format
                image_file_name = str(filename)
                name_split = image_file_name.split(".")
                extension = name_split[-1].upper()
                allowed_extensions = ["JPG", "JPEG", "PNG"]

                if extension in allowed_extensions:
                    print("Extension Exists")
                    # loading image using cv2
                    try:
                        image_np = cv2.imread(filename, 1)
                        image_np = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
                        image_np = cv2.resize(image_np, (800, 600))
                    except Exception as e:
                        print('Error with image file properties', e)

                    # deleting previous cropped image files present in detected_number_plate
                    delete_files = './detected_number_plate'
                    for img in os.listdir(delete_files):
                        try:
                            os.remove(os.path.join(delete_files, img))
                        except Exception as e:
                            print("Error in deleting", e)

                    try:
                        with detection_graph.as_default():
                            with tf.compat.v1.Session(graph=detection_graph) as sess:
                                # Max No of number plates you want to detect from one image
                                num_plate_detect = 1
                                score_thresh = 0.5
                                image_np_expanded = np.expand_dims(image_np, axis=0)
                                image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
                                boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
                                scores = detection_graph.get_tensor_by_name('detection_scores:0')
                                classes = detection_graph.get_tensor_by_name('detection_classes:0')
                                num_detections = detection_graph.get_tensor_by_name('num_detections:0')

                                img_height, img_width, img_channel = image_np.shape

                                (boxes, scores, classes, num_detections) = sess.run(
                                    [boxes, scores, classes, num_detections],
                                    feed_dict={image_tensor: image_np_expanded}
                                )

                                boxes = np.squeeze(boxes)
                                classes = np.squeeze(classes).astype(np.int32)
                                scores = np.squeeze(scores)

                                # saving bbox images
                                image_np1 = cv2.imread(filename, 1)
                                image_np1 = cv2.cvtColor(image_np1, cv2.COLOR_BGR2RGB)
                                image_np1 = cv2.resize(image_np1, (800, 600))

                                min_score_thresh = 0.20
                                for j in range(0, num_plate_detect):
                                    true_boxes = boxes[j][scores[j] > min_score_thresh]
                                    for i in range(true_boxes.shape[0]):
                                        ymin = int(true_boxes[i, 0] * img_height)
                                        xmin = int(true_boxes[i, 1] * img_width)
                                        ymax = int(true_boxes[i, 2] * img_height)
                                        xmax = int(true_boxes[i, 3] * img_width)

                                        ymax = ymax + 30
                                        xmax = xmax + 30
                                        ymin = ymin - 20
                                        xmin = xmin - 20

                                        detected_images = './detected_number_plate/'
                                        roi = image_np1[ymin:ymax, xmin:xmax]
                                        cv2.imwrite(detected_images + f"box_{str(j)}.png", roi)

                                    print("Saved images Successfully")

                    except Exception as e:
                        return "Something Went Wrong....Unable to Detect. Please try again."

                    # Now convert cropped images into text using EasyOCR
                    try:
                        list_of_files = os.listdir("./detected_number_plate")
                        no_of_images = len(list_of_files)

                        for k in range(0, no_of_images):
                            output = reader.readtext(detected_images + f'box_{str(k)}.png')
                            final_output = output[0][1]

                    except Exception as e:
                        return "Something Went Wrong....Unable to do OCR. Please try again."

                    # Extracting state from extracted Number text
                    try:
                        first_state = []
                        final_output = final_output.replace(" ", "")

                        for i in range(len(final_output)):
                            if final_output[i].isalpha():
                                if len(first_state) != 2:
                                    first_state.append(final_output[i])

                        # initialise empty string
                        code = "".join(first_state).upper()
                        final_state = states[code]

                        # Sending map images url and state name to HTML
                        image_name1 = "./static/maps/" + str(code) + ".jpg"
                        state_and_no = str(final_state) + " :- " + str(final_output)

                        return render_template('show_map.html', image_name1=image_name1, state_name=state_and_no)

                    except Exception as e:
                        return "Something Went Wrong....Text extraction error. Please try again."

                else:
                    return 'Error: Please make sure that image file is in standard acceptable extension.'

            else:
                return 'File Not Found'

        except Exception as e:
            print('The Exception message is: ', e)
            return 'something is wrong'

    else:
        return render_template('index.html')


@app.route('/uploadfile', methods=['POST', 'GET'])  #
@cross_origin()
def uploadfile():
    return render_template('upload.html')


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)

