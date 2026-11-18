"""Consistent chart grammar: teal = prices, amber = differences, blue = coverage."""
import altair as alt
import pandas as pd
import streamlit as st

TEAL='#087f78'
AMBER='#d69836'
BLUE='#5586ad'
PALETTE=[TEAL,BLUE,AMBER,'#a277a0','#86ae94','#b56363','#6c7cba','#bd9a71']

def draw(chart, key=None):
    styled=chart.configure_view(stroke=None).configure_axis(
        labelColor='#55666a', titleColor='#55666a', gridColor='#e8eeeb',
        domain=False, tickColor='#d8e2df', labelFontSize=11, titleFontSize=11,
        titlePadding=12).configure_legend(labelColor='#55666a', titleColor='#344d4a',
        orient='bottom', labelFontSize=11).configure_title(anchor='start',color='#173d37')
    return st.altair_chart(styled,width='stretch',key=key)

def calendar(daily):
    order=daily.month.drop_duplicates().tolist()
    return alt.Chart(daily).mark_rect(cornerRadius=3,stroke='#fbfcfa',strokeWidth=2).encode(
        x=alt.X('day:O',title='Day of month',axis=alt.Axis(labelAngle=0)),
        y=alt.Y('month:N',sort=order,title=None),
        color=alt.condition('datum.observations > 0',alt.Color('observations:Q',scale=alt.Scale(scheme='teals'),legend=alt.Legend(title='Observations',format='~s')),alt.value('#e6eae7')),
        tooltip=[alt.Tooltip('date:T',title='Date',format='%d %b %Y'),alt.Tooltip('observations:Q',title='Eligible observations',format=',')]
    ).properties(height=max(150,len(order)*25))

def histogram(sample):
    bars=alt.Chart(sample[['price']]).mark_bar(color=TEAL,opacity=.85,cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(
        x=alt.X('price:Q',bin=alt.Bin(maxbins=26),title='Observed price (RM / unit)'),
        y=alt.Y('count():Q',title='Shops'),tooltip=[alt.Tooltip('price:Q',bin=alt.Bin(maxbins=26),format='.2f',title='Price band'),alt.Tooltip('count():Q',title='Shops')])
    median=alt.Chart(pd.DataFrame({'median':[sample.price.median()]})).mark_rule(color=AMBER,strokeWidth=2,strokeDash=[5,4]).encode(x='median:Q',tooltip=[alt.Tooltip('median:Q',format='.2f',title='Median (RM)')])
    return (bars+median).properties(height=280)

def geographic_ranges(geo,by):
    base=alt.Chart(geo).encode(y=alt.Y(f'{by}:N',sort=alt.SortField('median',order='ascending'),title=None),tooltip=[alt.Tooltip(f'{by}:N',title='Location'),alt.Tooltip('median:Q',title='Median (RM)',format='.2f'),alt.Tooltip('lower:Q',title='25th percentile',format='.2f'),alt.Tooltip('upper:Q',title='75th percentile',format='.2f'),alt.Tooltip('premises:Q',title='Shops')])
    spread=base.mark_rule(color='#a7d1c5',strokeWidth=6).encode(x=alt.X('lower:Q',title='Observed price (RM / unit)',scale=alt.Scale(zero=False)),x2='upper:Q')
    point=base.mark_circle(color=TEAL,size=70).encode(x='median:Q')
    return (spread+point).properties(height=max(220,min(640,len(geo)*24)))

def ranking(data,value='price',label='shop_label',height=None):
    base=alt.Chart(data).encode(y=alt.Y(f'{label}:N',sort=alt.SortField(value,order='ascending'),title=None,axis=alt.Axis(labelLimit=235)),x=alt.X(f'{value}:Q',title='Observed cost (RM)',scale=alt.Scale(zero=True)),tooltip=[alt.Tooltip(f'{label}:N',title='Shop'),alt.Tooltip(f'{value}:Q',title='Cost (RM)',format='.2f')])
    return (base.mark_bar(color=TEAL,opacity=.85,cornerRadiusEnd=4)+base.mark_text(align='left',dx=5,color='#344d4a').encode(text=alt.Text(f'{value}:Q',format='.2f'))).properties(height=height or max(200,len(data)*29))

def trend_ribbon(trend):
    brush=alt.selection_interval(encodings=['x'],name='time_window')
    hover=alt.selection_point(fields=['date'],nearest=True,on='pointerover',empty=False,clear='pointerout',name='date_hover')
    base=alt.Chart(trend).encode(x=alt.X('date:T',title=None,scale=alt.Scale(domain=brush)))
    ribbon=base.mark_area(color=TEAL,opacity=.14).encode(y=alt.Y('lower:Q',title='Observed price (RM)',scale=alt.Scale(zero=False)),y2='upper:Q')
    line=base.mark_line(color=TEAL,strokeWidth=2.5).encode(y='median:Q')
    dots=base.mark_circle(color=TEAL,size=65).encode(y='median:Q',opacity=alt.condition(hover,alt.value(1),alt.value(0)),tooltip=[alt.Tooltip('date:T',title='Period ending',format='%d %b %Y'),alt.Tooltip('median:Q',title='Median (RM)',format='.2f'),alt.Tooltip('lower:Q',title='25th percentile',format='.2f'),alt.Tooltip('upper:Q',title='75th percentile',format='.2f'),alt.Tooltip('observations:Q',title='Observations'),alt.Tooltip('premises:Q',title='Shops')]).add_params(hover)
    focus=(ribbon+line+dots).properties(height=290)
    context=alt.Chart(trend).mark_bar(color=BLUE,opacity=.6).encode(x=alt.X('date:T',title='Drag across this strip to zoom into a period'),y=alt.Y('observations:Q',title='Records',axis=alt.Axis(format='~s'))).add_params(brush).properties(height=65)
    return alt.vconcat(focus,context,spacing=12).properties(autosize=alt.AutoSizeParams(type='fit-x',contains='padding'))

def state_heatmap(data):
    work=data.assign(month=data.date.dt.to_period('M').dt.to_timestamp())
    heat=work.groupby(['state','month'],observed=True).agg(median=('price','median'),observations=('price','size')).reset_index()
    return alt.Chart(heat).mark_rect(cornerRadius=3,stroke='#fbfcfa',strokeWidth=2).encode(
        x=alt.X('month:O',sort=sorted(heat.month.unique()),title=None,axis=alt.Axis(labelExpr="timeFormat(toDate(datum.value), '%b %Y')",labelAngle=-35)),
        y=alt.Y('state:N',title=None),color=alt.Color('median:Q',title='Median (RM)',scale=alt.Scale(scheme='teals',zero=False)),
        tooltip=[alt.Tooltip('state:N',title='State'),alt.Tooltip('month:T',format='%b %Y',title='Month'),alt.Tooltip('median:Q',format='.2f',title='Median (RM)'),alt.Tooltip('observations:Q',title='Observations')]).properties(height=max(160,heat.state.nunique()*26))

def basket_stack(rows,order):
    rows=rows.copy()
    rows['product_label']=rows['item'].astype(str).str.slice(0,48)+' · #'+rows['item_code'].astype(str)
    return alt.Chart(rows).mark_bar().encode(y=alt.Y('shop_label:N',sort=order,title=None,axis=alt.Axis(labelLimit=210)),x=alt.X('sum(line_total):Q',title='Complete basket total (RM)'),color=alt.Color('product_label:N',title='Product',scale=alt.Scale(range=PALETTE),legend=alt.Legend(labelLimit=260)),tooltip=[alt.Tooltip('shop_label:N',title='Shop'),alt.Tooltip('item:N',title='Product'),alt.Tooltip('quantity:Q',title='Quantity'),alt.Tooltip('line_total:Q',title='Item cost (RM)',format='.2f')]).properties(height=max(200,len(order)*38))
