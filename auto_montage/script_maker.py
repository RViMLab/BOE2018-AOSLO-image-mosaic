import csv
import numpy as np
import os


def create_preferences(jsfile):
    jsfile.write("""
app.preferences.rulerUnits = Units.PIXELS
app.preferences.typeUnits = TypeUnits.PIXELS
app.displayDialogs = DialogModes.NO
var color = new SolidColor()
color.gray.gray = 100
""")


def create_function(jsfile):
    jsfile.write("""
var AVG = 0
var SPLIT = 1
var CONF = 2
var names = ["avg", "split_det", "confocal"]

function addLinkedImage(confocal_fname, dx, dy, doc) {
	
	var docRef = docs[doc]
	var split_fname = confocal_fname.replace(names[CONF], names[SPLIT])
	var avg_fname = confocal_fname.replace(names[CONF], names[AVG])
	
	var file_names = [avg_fname, split_fname, confocal_fname]

	// input the three image types into there layersets
	for (var imageType = 0; imageType < 3; imageType++){
		// open new document with just the image so we can duplicate to montage
		var img = new File(file_names[imageType]);
		var opened = open(img);
		var pSourceDocument = app.activeDocument;
		pSourceDocument.artLayers[0].duplicate(docRef);
		pSourceDocument.close()
		
		// get the layer in the montage document
		var layerInOrig = docRef.artLayers[0]
		var image_name = file_names[imageType].split('\\\\')
		layerInOrig.name = image_name[image_name.length - 1]
		layerInOrig.move(docRef.layerSets.getByName(names[imageType]),  ElementPlacement.INSIDE)
	}
	
	// link the three images
	for (var imageType = 0; imageType < 2; imageType++) {
		var layersetOne = docRef.layerSets.getByName(names[imageType])
		var layersetTwo = docRef.layerSets.getByName(names[imageType + 1])
		var image_one_name = file_names[imageType].split('\\\\')
		var artLayerOne = layersetOne.artLayers.getByName(image_one_name[image_one_name.length - 1])
		var image_two_name = file_names[imageType + 1].split('\\\\')
		var artLayerTwo = layersetTwo.artLayers.getByName(image_two_name[image_two_name.length - 1])
		
		artLayerOne.link(artLayerTwo)
		layersetOne.visible = false
	}
	
	// add resizing to canvas
	var confocal_layer_set = docRef.layerSets.getByName(names[CONF])
	var confocal_name = file_names[CONF].split('\\\\')
	var confocal_image_layer = confocal_layer_set.artLayers.getByName(confocal_name[confocal_name.length - 1])
	confocal_image_layer.translate(dx, dy)
}

for (var disjoint = 0; disjoint<docs.length; disjoint++){
	var translations = data[disjoint]
	app.activeDocument = docs[disjoint]
	for (var i = 0; i<translations.length; i++) {
		var d = translations[i]
		var confocal_name = d[0]
		var ty = d[1]
		var tx = d[2]
		addLinkedImage(confocal_name, ty, tx, disjoint)
	}
	docs[disjoint].revealAll()
}
""")


def get_doc_add_layerset(doc):
    return """
app.activeDocument = docs[""" + str(doc) + """]
app.activeDocument.selection.fill(color, ColorBlendMode.NORMAL, 100, false)
var docRef = docs[""" + str(doc) + """]
var confocal = docRef.layerSets.add()
confocal.name = "confocal"
var split = docRef.layerSets.add()
split.name = "split_det"
var avg = docRef.layerSets.add()
avg.name = "avg"
"""
    return script_js


def create_doc(doc):
    return 'app.documents.add(10000, 10000, 72, "montage' + str(doc) + '", NewDocumentMode.GRAYSCALE)'


def create_transformations(jsfile, disjoint_montage):
    for disjoint in range(len(disjoint_montage)):
        jsfile.write('var data' + str(disjoint) + ' = [')

        trans_for_join = []
        for transformation in disjoint_montage[disjoint]:
            confocal_name = transformation['confocal']
            ty = float(transformation['transy'])
            tx = float(transformation['transx'])

            # if global_ref set its height
            if tx == 0.0 and ty == 0.0:
                global_height = int(transformation['h'])
                global_width = int(transformation['w'])

            height = int(transformation['h'])
            width = int(transformation['w'])
            trans_for_join.append(
                str([
                    confocal_name,
                    float(ty) + (width - global_width) / 2.,
                    float(tx) + (height - global_height) / 2.]))

        data = ','.join(trans_for_join)
        jsfile.write(data)
        jsfile.write(']\n')
    return len(disjoint_montage)


def create_array_of_data(jsfile, chunks):
    jsfile.write('var data = [')
    montage_js = []
    for disjoint_montage in range(chunks):
        montage_js.append('data' + str(disjoint_montage))
    montage_js_as_string = ','.join(montage_js)
    jsfile.write(montage_js_as_string)
    jsfile.write(']\n')


def create_doc_array(jsfile, chunks):
    jsfile.write('var docs = [')
    docs_js = []
    for doc in range(chunks):
        docs_js.append(create_doc(doc))
    docs_js_as_string = ','.join(docs_js)
    jsfile.write(docs_js_as_string)
    jsfile.write(']\n')


def create_layer_sets(jsfile, chunks):
    for doc in range(chunks):
        jsfile.write(get_doc_add_layerset(doc))


def write_photoshop_script(disjoint_montages, photoshop_directory, name=None):
    fname = 'create_recent_montage.jsx' if name is None else name + '.jsx'
    with open(os.path.join(photoshop_directory, fname), 'w') as jsfile:
        # preferences, units etc
        create_preferences(jsfile)

        # creating arrays with the translations and file names
        # will have to find the right folder
        chunks = create_transformations(jsfile, disjoint_montages)

        # puts the previous arrays into a single array
        create_array_of_data(jsfile, chunks)

        # creates required number of docs
        create_doc_array(jsfile, chunks)

        # add the layersets to these docs
        create_layer_sets(jsfile, chunks)

        # write the ending script which has the function
        create_function(jsfile)
