"""State coverage choropleth using official DOSM administrative geometry."""
import json
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

BOUNDARIES = Path(__file__).parent / 'assets' / 'malaysia_states.geojson'
SOURCE = 'https://github.com/dosm-malaysia/data-open/blob/main/datasets/geodata/administrative_1_state.geojson'

def select_map_state():
    event = st.session_state.get('coverage_map', {})
    picked = event.get('selection', {}).get('state_pick', [])
    if picked:
        name = picked[0].get('region')
        if name:
            st.session_state['state_False'] = name
            st.session_state['district_False'] = 'All districts'

def reset_map_state():
    st.session_state['state_False'] = 'All Malaysia'
    st.session_state['district_False'] = 'All districts'

@st.cache_data(max_entries=2, show_spinner=False)
def coverage_summary(_data, signature):
    # Cache the small summary rather than hashing the full observation table.
    return _data.groupby(['state', 'district'], observed=True).agg(
        observations=('price', 'size'), premises=('premise_code', 'nunique'),
        products=('item_code', 'nunique'), latest=('date', 'max')).reset_index()

@st.cache_data(max_entries=1, show_spinner=False)
def state_summary(_data, signature):
    return _data.groupby('state', observed=True).agg(
        observations=('price', 'size'), premises=('premise_code', 'nunique'),
        products=('item_code', 'nunique'), latest=('date', 'max')).reset_index()

def coverage_features(summary):
    geometry = json.loads(BOUNDARIES.read_text(encoding='utf-8'))
    records = summary.set_index('state').to_dict('index')
    for feature in geometry['features']:
        state = feature['properties']['state']
        record = records.get(state)
        properties = feature['properties']
        properties['scope'] = 'Within selection' if record else 'Outside selection / no eligible observations'
        for key in ['observations', 'premises', 'products']:
            properties[key] = int(record[key]) if record else None
        properties['latest'] = pd.Timestamp(record['latest']).strftime('%d %b %Y') if record else '—'
    return geometry['features']

def coverage_map(data, state, district, signature):
    with st.container(border=True):
        title, action = st.columns([4, 1], vertical_alignment='bottom')
        title.subheader('Malaysia retail coverage')
        action.button('Reset map', on_click=reset_map_state, width='stretch', icon=':material/public:')
        metric = st.segmented_control('Colour map by', ['Surveyed premises', 'Price observations', 'Monitored products'], default='Surveyed premises', key='map_metric')
        if district == 'All districts':
            summary = state_summary(data, signature)
        else:
            summary = coverage_summary(data, signature)
            summary = summary[summary.district == district]
        if state != 'All Malaysia':
            summary = summary[summary.state == state]
        field = {'Surveyed premises': 'premises', 'Price observations': 'observations', 'Monitored products': 'products'}[metric or 'Surveyed premises']
        pick = alt.selection_point(fields=['region'], name='state_pick', toggle=False, on='click')
        chart = alt.Chart(alt.Data(values=coverage_features(summary))).transform_calculate(region='datum.properties.state').mark_geoshape(stroke='#ffffff', strokeWidth=0.8).encode(
            color=alt.condition(f'isValid(datum.properties.{field})',
                alt.Color(f'properties.{field}:Q', title=metric, scale=alt.Scale(scheme='teals'), legend=alt.Legend(orient='bottom', format=',.0f')),
                alt.value('#e1e7e4')),
            tooltip=[alt.Tooltip('properties.state:N', title='State / territory'),
                     alt.Tooltip('properties.scope:N', title='Coverage'),
                     alt.Tooltip('properties.premises:Q', title='Surveyed premises', format=',.0f'),
                     alt.Tooltip('properties.observations:Q', title='Eligible observations', format=',.0f'),
                     alt.Tooltip('properties.products:Q', title='Monitored products', format=',.0f'),
                     alt.Tooltip('properties.latest:N', title='Latest observation')]
        ).project(type='mercator').properties(height=360).add_params(pick)
        st.altair_chart(chart, width='stretch', key='coverage_map', on_select=select_map_state)
        st.caption(f'Click a state to filter the atlas · Hover for counts · {state} / {district} · Full supplied date coverage. Areas represent aggregated coverage, not individual shop locations.')
        st.caption(f'[Boundary source: DOSM]({SOURCE}) · Grey areas are outside your selection or have no eligible observations.')
