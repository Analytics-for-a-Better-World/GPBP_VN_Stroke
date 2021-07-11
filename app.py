from flask import Flask, flash, redirect, render_template, request, session, abort  
from flask_cors import CORS,cross_origin
import pandas as pd
import geopy.distance
import json
import requests
import folium

app = Flask(__name__,static_url_path='/static')
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy   dog'
app.config['CORS_HEADERS'] = 'Content-Type'
cors = CORS(app, resources={r"/foo": {"origins": "http://localhost:port"}})


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
			request_mapbox_driving = """https://api.mapbox.com/directions-matrix/v1/mapbox/driving-traffic/"""+(coordinate_str)+"""?annotations=duration&access_token=pk.eyJ1IjoicGFydmF0aHlrcmlzaG5hbmsiLCJhIjoiY2sweWVkOHcxMDBodDNpbm1ueXY2bzl1OCJ9.c93KNq0W0VtUq4FCD3XxJg"""
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

	return render_template('dashboard.html',ACCESS_KEY='pk.eyJ1IjoicGFydmF0aHlrcmlzaG5hbmsiLCJhIjoiY2sweWVkOHcxMDBodDNpbm1ueXY2bzl1OCJ9.c93KNq0W0VtUq4FCD3XxJg',
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
@cross_origin(origin='localhost',headers=['Content- Type','Authorization'])
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
		hosp_options = [0,10,20,50,100]

		if "radio_dist" in request.form:
			selected_dist = request.form['radio_dist']
			selected_hosp_count = request.form['sel1']

			model_name = request.form['model_sel']
			folder_name_model = 'static/data/optimization/'+model_name+'/'

			df_opt_outputs = pd.read_pickle(folder_name_model+'df_opt_outputs.pkl')
			df_cordinates_hosp = pd.read_pickle(folder_name_model+'df_cordinates_hosp.pkl')
			population = pd.read_pickle(folder_name_model+'population.pkl')
			current_hospitals = pd.read_pickle(folder_name_model+'current_hospitals.pkl')


			n = population['ID'].nunique()

			opt_sel_df= df_opt_outputs[(df_opt_outputs['km']==int(selected_dist)) & (df_opt_outputs['number_of_new_hospitals']==int(selected_hosp_count))]

			hosp_present = opt_sel_df['array_hosp'].values[0]
			df_cordinates_hosp = df_cordinates_hosp.sort_values(by='Hosp_ID')
			df_cordinates_hosp['present_index'] = hosp_present
			only_present_health_fac = df_cordinates_hosp[df_cordinates_hosp.present_index==1]	

			population = population.sort_values(by='ID')
			served1_population = population[['ID','xcoord','ycoord','household_count']]
			x = opt_sel_df['array_hh'].values[0]
			x1 = x[:n]
			served1_population['served']=x1

			served_population = served1_population[served1_population['served']==1]

			served_population['x_roun'] =  served_population['xcoord'].round(3)
			served_population['y_roun'] =  served_population['ycoord'].round(3)
			served_population['household_count'] = served_population['household_count'].round()
			served = served_population.groupby(['x_roun','y_roun','served'])['household_count'].sum().reset_index()

			#unserved_population = served1_population[served1_population['served']==0]
			#unserved_population['x_roun'] =  unserved_population['xcoord'].round(1)
			#unserved_population['y_roun'] =  unserved_population['ycoord'].round(1)
			#unserved_population['household_count'] = unserved_population['household_count'].round()
			#unserved = unserved_population.groupby(['x_roun','y_roun','served'])['household_count'].sum().reset_index()

			def get_color(x,q1,q2,q3):
			    if(x<=q1):
			        return 0.1
			    else:
			        if(x<=q2):
			            return 0.3
			        else:
			            if(x<=q3):
			                return 0.5
			            else:
			                return 1

			q1 = served['household_count'].describe()['25%']
			q2 = served['household_count'].describe()['50%']
			q3 = served['household_count'].describe()['75%']
			served['opacity'] = served['household_count'].apply(get_color,q1=q1,q2=q2,q3=q3)

			#q1 = unserved['household_count'].describe()['25%']
			#q2 = unserved['household_count'].describe()['50%']
			#q3 = unserved['household_count'].describe()['75%']
			#unserved['opacity'] = unserved['household_count'].apply(get_color,q1=q1,q2=q2,q3=q3)

			map_osm = folium.Map(location=[16, 106],zoom_start=5,prefer_canvas=True)

			for x in only_present_health_fac.values:
			    hosp_name = x[0]
			    lon = x[1]
			    lat = x[2]
			    
			    if(hosp_name in current_hospitals['Hosp_ID'].unique()):
			        color_marker = 'green'
			    else:
			        color_marker = 'blue'
			    folium.Marker([lat,lon],icon=folium.Icon(color=color_marker,icon='hospitals', prefix='fa',size=1)).add_to(map_osm)

			for each_val in served.values:
			    lon = each_val[0]
			    lat = each_val[1]
			    
			    hh_count = each_val[3]
			    color_circle = 'green'
			    opacity = each_val[4]

			    folium.Circle(location=[lat,lon],radius=10,color=color_circle,fill_color=color_circle,opacity=opacity).add_to(map_osm)

			#for each_val in unserved.values:
			#    lon = each_val[0]
			#    lat = each_val[1]
			    
			#    hh_count = each_val[3]
			#    color_circle = 'red'
			#    opacity = each_val[4]

			#    folium.Circle(location=[lat,lon],radius=10,color=color_circle,fill_color=color_circle,opacity=opacity).add_to(map_osm)

			map_osm.save('static/data/map_render.html')

	return render_template('optimization.html',model_selected=model_name,km_options=km_options,hosp_options=hosp_options,folder_name=folder_name,
		selected_dist=selected_dist,selected_hosp_count=selected_hosp_count)

if __name__ == '__main__':
    app.run(debug=False)


 
