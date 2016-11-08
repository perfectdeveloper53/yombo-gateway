from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_atoms(webapp):
    with webapp.subroute("/atoms") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_atoms(webinterface, request, session):
            return webinterface.redirect(request, '/atoms/index')

        @webapp.route('/index')
        @require_auth()
        def page_atoms_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/atoms/index.html')
            i18n = webinterface.i18n(request)
            return page.render(alerts=webinterface.get_alerts(),
                               atoms=webinterface._Libraries['atoms'].get_atoms(),
                               _=i18n,
                               )