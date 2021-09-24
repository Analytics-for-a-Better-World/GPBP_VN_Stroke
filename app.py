from flask import Flask, flash, redirect, render_template, request, session, abort  
import pandas as pd
import geopy.distance
import json
import requests
import folium
import pickle

app = Flask(__name__,static_url_path='/static')

@app.route('/', methods=["GET", "POST"])
def dashboard():
	df_stroke_facs = pd.read_csv('static/data/stroke-facs.csv')
	df_stroke_facs = df_stroke_facs[['Contracted with VSS? (1=yes; 2=no)','Facility level (Trung ương=central; tỉnh=provincial; huyện=district)',
						'Facility name-VN','Name_English','Facility type-VN','Type_name','Sectoral (1:health sector; 2:other sector;3:private sector)','address',
						'longitude','latitude','phone','hyperlink']].reset_index()

	fac_details = []

	if(request.method=='POST'):
		latitude = request.form.get('latitude')
		longitude = request.form.get('longitude')

		stroke_facs_selected = df_stroke_facs[['index','latitude','longitude']]

		euclidean_distance_array = []
		for each_val in stroke_facs_selected.values:
			dist = geopy.distance.geodesic((latitude,longitude),(each_val[1],each_val[2]))
			dist_km = dist.meters/1000
			euclidean_distance_array.append([str(each_val[0]),dist_km])

		selected_feature = {
						'type': 'Feature',
				        'properties': {
				        'description': 'You selected this location!',
				        'icon': 'circle-15'
				        },
				        'geometry': {
				        'type': 'Point',
				        'coordinates': [longitude, latitude]
				        }
					}
		fac_details.append(selected_feature)

		df_euc_dist = pd.DataFrame(euclidean_distance_array)
		df_euc_dist.columns = ['index','euc_dist']
		df_euc_dist_sel = df_euc_dist.sort_values(by='euc_dist').head(5)

		df_stroke_facs['index'] = df_stroke_facs['index'].astype(float)
		df_euc_dist_sel['index'] = df_euc_dist_sel['index'].astype(float)
		df_euc_dist_sel = pd.merge(df_euc_dist_sel,df_stroke_facs,on='index')

		duration_array = []
		for each_val in df_euc_dist_sel.values:
			coordinate_str = str(longitude)+','+str(latitude)+';'+str(each_val[10])+','+str(each_val[11])
			request_mapbox_driving = """https://api.mapbox.com/directions-matrix/v1/mapbox/driving-traffic/"""+(coordinate_str)+"""?annotations=duration&access_token=pk.eyJ1IjoicGFydmF0aHlrcmlzaG5hbmsiLCJhIjoiY2tybGFoMTZwMGJjdDJybnYyemwxY3QxMSJ9.FXaVYsMF3HIzw7ZQFQPhSw"""
			duration_minutes = json.loads(requests.get(request_mapbox_driving).content)['durations'][0][1]/(60*60)
			duration_array.append(round(duration_minutes,1))
		df_euc_dist_sel['distance_mapbox'] = duration_array

		less_than_6 = df_euc_dist_sel[df_euc_dist_sel['distance_mapbox']<=6]

		for each_val in less_than_6.values:
			each_fac_feature = {
			        'type': 'Feature',
			        'properties': {
			        'description':
			        '<strong>'+str(each_val[4])+'</strong><p><a href="'+str(each_val[13])+'" target="_blank">'+str(each_val[5])+'</a> is '+str(each_val[14])+' hours by driving in traffic'+'</p><form method="POST" action="/isochrones"><input hidden id="my_input" type="text" name="HTMLControlName" value="'+each_val[4]+'"><input type="submit" value="View Isochrones"></form>',
			        'icon': 'hospital-15'
			        },
			        'geometry': {
			        'type': 'Point',
			        'coordinates': [each_val[10], each_val[11]]
			        }
			        }
			fac_details.append(each_fac_feature)


	else:
		for each_val in df_stroke_facs.values:
			each_fac_feature = {
			        'type': 'Feature',
			        'properties': {
			        'description':
			        '<strong>'+str(each_val[3])+'</strong><p><a href="'+str(each_val[12])+'" target="_blank">'+str(each_val[4])+'</a> is a '+str(each_val[2])+' stroke facility'+'</p><form method="POST" action="/isochrones"><input hidden id="my_input" type="text" name="HTMLControlName" value="'+each_val[4]+'"><input type="submit" value="Submit"></form>',
			        'icon': 'hospital-15'
			        },
			        'geometry': {
			        'type': 'Point',
			        'coordinates': [each_val[9], each_val[10]]
			        }
			        }
			fac_details.append(each_fac_feature)

	return render_template('dashboard.html',ACCESS_KEY='pk.eyJ1IjoicGFydmF0aHlrcmlzaG5hbmsiLCJhIjoiY2tybGFoMTZwMGJjdDJybnYyemwxY3QxMSJ9.FXaVYsMF3HIzw7ZQFQPhSw',
		stroke_facs=fac_details)

@app.route('/isochrones', methods=["POST"])
def isochrones():
	if(request.method=='POST'):
		sel_name = request.form.get('HTMLControlName')
		df_stroke_facs = pd.read_csv('static/data/stroke-facs.csv')
		sel_fac = df_stroke_facs[df_stroke_facs['Name_English']==sel_name][['longitude','latitude']].values
		longitude = sel_fac[0][0]
		latitude = sel_fac[0][1]
		return render_template('isochrones.html',longitude=longitude,latitude=latitude) 


@app.route('/optimization', methods=["GET", "POST"])
def analyze():
	model_name = 9999
	km_options = []
	hosp_options = []
	folder_name = 9999
	selected_dist = 9999
	selected_hosp_count = 9999
	file_map_save = 9999
	
	if request.method=='POST':
		model_name = request.form['model_sel']
		folder_name = '/static/data/optimization/'+model_name+'/pareto.html'
		km_options = [10,20,50]
		hosp_options = [0,10,20,50]

		if "radio_dist" in request.form:
			selected_dist = request.form['radio_dist']
			selected_hosp_count = request.form['sel1']

			model_name = request.form['model_sel']
			file_map_save = 'static/data/optimization/'+model_name+'/maps/'+str(selected_dist)+'_'+str(selected_hosp_count)+'_map_render.html'
			file_map_save = '/'+file_map_save

	return render_template('optimization.html',model_selected=model_name,km_options=km_options,hosp_options=hosp_options,folder_name=folder_name,
		selected_dist=selected_dist,selected_hosp_count=selected_hosp_count,file_map_save=file_map_save)

if __name__ == '__main__':
    app.run(debug=True)


 
