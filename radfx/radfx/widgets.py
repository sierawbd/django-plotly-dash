import json,base64

import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_table
from dash_table.Format import Format, Scheme, Sign, Symbol
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
import json,base64
import numpy as np
###############################################################################
# Theming
###############################################################################
import plotly.io as pio
pio.templates['radfx'] = go.layout.Template(
    layout={
        'margin': dict({'t': 10}),
        'xaxis': {
            'title': {'font': {'size': 14}},
            'tickfont': {'size': 14},
        },
        'yaxis': {
            'title': {'font': {'size': 14}},
            'tickfont': {'size': 14},
        }
    }
)
pio.templates.default = "simple_white+radfx"
max_upload_size=5 * 2**20 # bytes


def card(title,body,dropdown=[]):
    htmldropdown=[]
    dropdownitems=[]

    if dropdown:
        #for (name,id) in dropdown:
        #    dropdownitems.append(html.Button(className="dropdown-item", id=id, children=[name]))
        dropdownitems=dropdown
        
        htmldropdown=[html.Div(className="dropdown no-arrow", children=[
            html.A(**{'className': "dropdown-toggle", 'href': "#",
                      'role': "button", 'id': "dropdownMenuLink",
                      'data-toggle': "dropdown"},
                   children=[
                       html.I(className="fas fa-ellipsis-v fa-sm fa-fw text-gray-400")
                   ]),
            html.Div(className="dropdown-menu dropdown-menu-right shadow animated--fade-in",
                     children=[
                         html.Div(className="dropdown-header", children=["Actions:"]),
                     ]+dropdownitems
            )
        ])]
        
    return html.Div(className='card shadow mb-4',children=[
        html.Div(className='card-header py-3 d-flex flex-row align-items-center justify-content-between ', children=[
            html.H6(className='m-0 font-weight-bold text-primary', children=title)]+htmldropdown
        ),
        html.Div(className='card-body', children=body)
    ])

class GraphCard:
    def __init__(self,app,id,title=None,data=[],layout=None,import_data=False,export_plot=True):
        self.id = id
        fig = go.Figure(data=data) # Uses default theme
        fig.update_layout(layout)
        self.graph_layout=fig.layout
        graph=dcc.Graph(id='%s-graph'%id,figure=fig)
        body=[graph,dcc.Download(id="%s-download"%id)]        
        dropdown=[]
        #if upload:
        #    body=[dcc.Upload(id="%s-upload"%id,
        #                   children=[graph],
        #                   max_size=max_upload_size,
        #                   multiple=False)]
        #    # lambda function is a hack for python3, not sure why it doesn't work otherwise
        #    app.callback([Output('%s-graph'%(self.id), 'figure')],
        #             [Input('%s-upload'%(self.id), 'contents')],
        #             [State('%s-upload'%(self.id), 'filename'),
        #              State('%s-upload'%(self.id), 'last_modified')])(lambda x,y,z: self.upload(x,y,z))
        if import_data:
            dropdown=dropdown+[dcc.Upload(id="%s-import-data"%id, children=[html.Button(className="dropdown-item", children=["Import data"])])]
            app.callback([Output('%s-graph'%(self.id), 'figure')],
                     [Input("%s-import-data"%id, 'contents')],
                     [State("%s-import-data"%id, 'filename'),
                      State("%s-import-data"%id, 'last_modified')])(lambda x,y,z: self.upload(x,y,z))
        if export_plot:
            #dropdown=dropdown+[("Export json plot","%s-export-plot"%id)]
            dropdown=dropdown+[html.Button(className="dropdown-item", id="%s-export-plot"%id, children=["Export json plot"]) ]
            app.callback([Output("%s-download"%id,"data")],
                         [Input("%s-export-plot"%id,"n_clicks")],
                         [State("%s-graph"%id,"figure")],
                         prevent_initial_call=True)(lambda x,y: self.download(json.dumps(y)))
            
        self.layout = card("%s"%title, dropdown=dropdown, body=body)
        
    def download(self,data):
        return [dict(content=data,filename="export.json")]
        
    def upload(self,contents,name,date):
        if not contents:
            return [{'layout': self.graph_layout,'data': None}]
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string).decode('ASCII')
        # Allow for custom parsing to return json data for figure
        data = self.parse(decoded)
        return self.update(data)
        
    def parse(self,data):
        data=json.loads(data)
        return data

    def update(self,data):
        return [ {'layout': self.graph_layout,'data': data} ]
        

class EnvironmentCard(GraphCard):
    def parse(self,data):
        # First try to parse as json format
        try:
            return json.loads(data)
        except:
            pass
        # If that fails, try a CREME96 flux file
        try:
            data = self.creme_flux(data)
            zs=data['Flux (/cm^2-s-sr-MeV)'].keys()
            #zs=set(zs)&set(['1','2','6','7','8','12','26'])
            return [{'name': z, 'x': list(data['Energy (MeV/n)']), 'y': list(data['Flux (/cm^2-s-sr-MeV)'][z]) } for z in zs]
        except:
            pass
        # If that fails, try a SPENVIS file
        try:
            data = self.spenvis_tri(data)
            zs=data.keys()
            #zs=set(zs)&set(['1','2','6','7','8','12','26'])
            return [{'name': z, 'x': list(data[z]['Energy (MeV/n)']), 'y': list(data[z]['Flux (/cm^2-s-sr-MeV)']) } for z in zs]
        except:
            pass
        # Otherwise, return nothing
        return []

    def creme_flux(self,data):
        """This function takes a legacy Creme96 flux file (.trp, .flx, or .tfx) output and returns the spectra for further processing."""
        spectra=[]
        lines=list(filter(None,data.split('\n')))
        # First line is always a file name and version tag
        tagline=lines.pop(0)
        (nComments,fname,vmajor,vminor)=tagline.split()
        
        # Split the comments from the data
        nComments=int(nComments)
        comments=lines[0:nComments]
        parameters=lines[nComments].split()
        data=lines[nComments+1:]
    
        # Read parameters
        (xmin,xmax)=[float(d) for d in parameters[0:2] ]
        (bins,z1,z2)=[int(d) for d in parameters[2:5] ]
    
        # Generate log spaced x-values (MeV/nucleon)
        energy=np.logspace(np.log10(xmin),np.log10(xmax),bins)
        yvals=np.genfromtxt(data,dtype=float)/1e4
        yvals=yvals.reshape((z2-z1+1,int(bins/6),6))
        flux=dict()
        for z in range(z1,z2+1):
            flux['%d'%z]=list(yvals[z-1].flatten())
    
        return dict({
            'Energy (MeV/n)': energy,
            'Flux (/cm^2-s-sr-MeV)': flux,
        })

    def spenvis_tri(self,data):
        lines=list(filter(None,data.split('\n')))
        blocks=[]

        while len(lines):
            # Header record
            tagline=lines[0]
            tags=tagline.split(',')
            assert(tags.pop(0) == "'*'")
            (Nh,Nc,Nm,Na,Nv,Nd,Nl,Nb)=[int(x) for x in tags]
            comments=lines[1:Nc+1]
            metadefs=dict()
            for m in lines[Nc+1:Nc+Nm+1]:
                t=m.split(',')
                ameta,ktyp=t[0:2]
                if int(ktyp) == -1:
                    metadefs[ameta.strip("\'")]=t[2].strip("\'")
                else:
                    metadefs[ameta.strip("\'")]=[x.strip("\'") for x in t[2:]]
            annotations=lines[Nc+Nm+1:Nc+Nm+Na+1]
            variables=lines[Nc+Nm+Na+1:Nc+Nm+Na+Nv+1]
            lines=lines[Nc+Nm+Na+Nv+1:]
            # Data record
            d=np.genfromtxt(lines[:Nl],dtype=float,delimiter=',')
            lines=lines[Nl:]
            end=lines[-1]
            assert(end == "'End of Block'" or 
                   end == "'End of File'")
            blocks.append(dict({'metadefs': metadefs, 'variables': variables, 'data': d}))
            lines=lines[1:]

        retval=dict()
        for b in blocks:
            if b['metadefs']['SPECIES'] == 'proton':
                z='1'
            if b['metadefs']['SPECIES'] == 'e-':
                z='-1'
            retval[z]=dict({
                'Energy (MeV/n)': list(b['data'][:,0]),
                'Flux (/cm^2-s-sr-MeV)': list(b['data'][:,2]/(4*3.14)),
            })
        return retval

class DataCard:
    def __init__(self,app,id,title=None,export_json=True):
        self.id=id

        dropdown=[]
        if export_json:
            dropdown=dropdown+[html.Button(className="dropdown-item", id="%s-export-data"%id, children=["Export json data"]) ]
            app.callback([Output("%s-download"%id,"data")],
                         [Input("%s-export-data"%id,"n_clicks")],
                         [State("%s-table"%id,"data")],
                         prevent_initial_call=True)(lambda x,y: self.download(json.dumps(y)))

        self.layout=card(title,body=[
            dash_table.DataTable(
                id='%s-table'%id,
                columns=([
                    {'id': 'id', 'name': 'Identifier', 'type': 'string'},
                    {'id': 'A', 'name': 'A', 'type': 'numeric'},
                    {'id': 'B', 'name': 'B', 'type': 'numeric'},
                    {'id': 'Rate', 'name': 'Rate (event/day)', 'type': 'numeric'},
                ]),
                css=[{'selector': 'table', 'rule': 'table-layout: fixed'}],
                style_data={
                    'whiteSpace': 'normal',
                },
                style_cell=[
                    {'width': '{}%'.format(4) }
                ],
                style_as_list_view=True,
                data=[
                    {'id': 'Id1', 'A': 10, 'B': 24, 'Rate': 0},
                    {'id': 'Id2', 'A': 20, 'B': 24, 'Rate': 0},
                    {'id': 'Id3', 'A': 10, 'B': 30, 'Rate': 0},
                ],
            ),
            dcc.Download(id="%s-download"%id)],
            dropdown=dropdown
        )

    def download(self,data):
        return [dict(content=data,filename="export.json")]
