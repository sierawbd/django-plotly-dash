errorModal = html.Div(
    [
        dbc.Button("Open modal", id="openError", n_clicks=0),
        dbc.Modal(
            [
                dbc.ModalHeader(["Error"],className="text-white bg-danger"),
                dbc.ModalBody("This is the content of the modal", id="errorMessage"),
                dbc.ModalFooter(
                    dbc.Button(
                        "Close", id="errorClose", n_clicks=0,                        
                    ),
                ),
            ],
            id="errorModal",
            centered=True,
            is_open=False,
        ),
    ]
)

#@app.callback(
#    Output("errorModal", "is_open"),
#    [Input("errorClose", "n_clicks"),Input("errorMessage", "children")]
#)
#def do_modal(n1,msg):
#    if n1 or not msg:
#        return False
#    return True

#@app.callback(
#    Output("errorModal", "is_open"),
#    [Input("errorClose", "n_clicks"),Input("errorMessage", "children")],
#    [State("errorModal", "is_open")],
#)
#def toggle_modal(n1, msg, is_open):
#    if n1 or not msg:
#        return False
#    return True

