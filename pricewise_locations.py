"""Folium geography with verified-coordinate gating; no address geocoding."""
import html
import json
import os
from pathlib import Path
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import streamlit as st
from pricewise_map import BOUNDARIES
from pricewise_core import DATA_DIR, maps_url

COORD_COLUMNS=['premise_code','latitude','longitude','source','verified_on']

def validate_coordinates(frame,shops):
    if not set(COORD_COLUMNS).issubset(frame.columns):
        raise ValueError('Coordinate file requires '+', '.join(COORD_COLUMNS))
    clean=frame.copy()
    for c in ['premise_code','latitude','longitude']:clean[c]=pd.to_numeric(clean[c],errors='coerce')
    dates=pd.to_datetime(clean.verified_on,errors='coerce')
    valid=(clean.latitude.between(-90,90)&clean.longitude.between(-180,180)&clean.premise_code.isin(shops.premise_code)&dates.notna()&clean.source.fillna('').astype(str).str.strip().ne('')&~clean.premise_code.duplicated(keep=False))
    return clean.loc[valid,COORD_COLUMNS].copy(),int((~valid).sum())

def coordinates(shops):
    path=Path(os.environ.get('PRICEWISE_COORDINATES',str(DATA_DIR/'verified_premise_coordinates.csv')))
    if not path.exists():return pd.DataFrame(columns=COORD_COLUMNS),0
    return validate_coordinates(pd.read_csv(path),shops)

def build_map(summary_json, outlet_json, state, cheapest=None):
    summary=json.loads(summary_json)
    outlets=json.loads(outlet_json)
    geometry=json.loads(BOUNDARIES.read_text(encoding='utf-8'))
    if state!='All Malaysia':geometry['features']=[f for f in geometry['features'] if f['properties']['state']==state]
    values=[v['median'] for v in summary.values() if v.get('median') is not None]
    scale=LinearColormap(['#e3f2ee','#77b9ae','#087f78'],vmin=min(values) if values else 0,vmax=max(values) if values and min(values)!=max(values) else ((max(values)+1) if values else 1),caption='Median observed product price (RM / listed unit)')
    m=folium.Map(location=[4.4,109.3],zoom_start=5,max_zoom=19,tiles=None,control_scale=True)
    # Folium consumes max_zoom for default tiles; no default tile layer exists here.
    # Set the Leaflet map option explicitly so MarkerCluster can initialize.
    m.options['max_zoom']=19
    folium.TileLayer('OpenStreetMap',name='Street map',show=False).add_to(m)
    for f in geometry['features']:
        rec=summary.get(f['properties']['state'],{})
        f['properties']['median_label']=f"RM {rec['median']:.2f}" if rec.get('median') is not None else 'No eligible observations'
        f['properties']['shops']=rec.get('shops',0)
        f['properties']['fill']=scale(rec['median']) if rec.get('median') is not None else '#e1e7e4'
    layer=folium.GeoJson(geometry,name='State price comparison',style_function=lambda f:{'fillColor':f['properties']['fill'],'color':'#536e67','weight':1,'fillOpacity':.85},highlight_function=lambda f:{'weight':3},tooltip=folium.GeoJsonTooltip(fields=['state','median_label','shops'],aliases=['State','Median price','Observed outlets']),zoom_on_click=True).add_to(m)
    if geometry['features']:m.fit_bounds(layer.get_bounds())
    if values:scale.add_to(m)
    cluster=MarkerCluster(name='Verified outlet locations').add_to(m)
    for r in outlets:
        winner=r['premise_code']==cheapest
        body=f"<b>{html.escape(str(r['premise']))}</b><br>{html.escape(str(r['address']))}<br>"
        if r.get('total') is not None:body+=f"Complete basket: RM {r['total']:.2f}<br>"
        if r.get('price') is not None:body+=f"Product price: RM {r['price']:.2f}<br>"
        if r.get('gross_saving') is not None:body+=f"Difference vs reference: RM {r['gross_saving']:.2f}<br>"
        body+=f"Observed: {html.escape(str(r.get('date',r.get('oldest','Not available'))))}<br>"
        body+=f"Coordinate source: {html.escape(str(r['source']))}<br>Verified: {html.escape(str(r['verified_on']))}<br>"
        body+=f'<a href="{html.escape(maps_url(r),quote=True)}" target="_blank" rel="noopener">Open directions</a>'
        folium.Marker([r['latitude'],r['longitude']],tooltip=f"{'Lowest complete basket · ' if winner else ''}{html.escape(str(r['premise']))} · #{r['premise_code']}",popup=folium.Popup(body,max_width=280),icon=folium.Icon(color='green' if winner else 'blue',icon='star' if winner else 'shopping-cart',prefix='fa')).add_to(cluster)
    folium.LayerControl(collapsed=True).add_to(m)
    return m

def render_location_map(latest,shops,state,key='retail_map',basket=None,baseline=None):
    try:
        coords,excluded=coordinates(shops)
    except (ValueError,OSError) as error:
        st.warning(f'Coordinate data unavailable: {error}')
        coords,excluded=pd.DataFrame(columns=COORD_COLUMNS),0
    summary=latest.groupby('state',observed=True).agg(median=('price','median'),shops=('premise_code','nunique')).to_dict('index') if basket is None else {}
    source=latest if basket is None else basket.merge(shops,on='premise_code')
    located=source.merge(coords,on='premise_code',how='inner')
    if baseline is not None and 'total' in located:located['gross_saving']=baseline-located.total
    cheapest=int(basket.premise_code.iloc[0]) if basket is not None and not basket.empty else None
    if coords.empty:
        st.info('Outlet pins unavailable: the supplied premise lookup has addresses but no verified coordinates. The map shows state-level geography; the outlet directory below provides address-based directions.')
    elif located.empty:st.info('No verified coordinates match outlets in this comparison.')
    if excluded:st.caption(f'{excluded} coordinate rows excluded for missing provenance, invalid coordinates or duplicate premise codes.')
    payload=(json.dumps(summary),located.to_json(orient='records',date_format='iso'),state,cheapest)
    cache_key=f'{key}_model_v3'
    cached=st.session_state.get(cache_key)
    if cached is None or cached[0]!=payload:
        cached=(payload,build_map(*payload))
        st.session_state[cache_key]=cached
    m=cached[1]
    # Folium's width=None is responsive; only marker selection triggers a rerun.
    event=st_folium(m,key=key,height=440,width=None,returned_objects=['last_object_clicked_tooltip'])
    if not located.empty:
        st.caption(f'{len(located):,} of {len(source):,} compared outlets have verified coordinates. Star: lowest complete basket; shopping cart: other outlet. No distance or route estimates are inferred.')
        picked=(event or {}).get('last_object_clicked_tooltip')
        if picked:
            matches=located[located.premise_code.map(lambda c:f'#{c}'==str(picked).split(' · ')[-1])]
            if not matches.empty:
                r=matches.iloc[0];st.success(f"Selected outlet: {r['premise']} — {r['address']}")
    st.caption('Boundaries: DOSM. Optional street tiles: OpenStreetMap. State shading describes the selected observations, not outlet coordinates. Map panning and zooming do not rerun the app.')
