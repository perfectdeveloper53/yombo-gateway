import socket
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.utils import random_string

def route_configs(webapp):
    with webapp.subroute("/configs") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_configs(webinterface, request, session):
            return webinterface.redirect(request, '/configs/basic')

        @webapp.route('/basic', methods=['GET'])
        @require_auth()
        def page_configs_basic_get(webinterface, request, session):
            configs = webinterface._Configs.get("*", "*")

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/configs/basic", "Basic Configs")
            return page.render(alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/basic', methods=['POST'])
        @require_auth(login_redirect="/configs/basic")
        @inlineCallbacks
        def page_configs_basic_post(webinterface, request, session):

            valid_submit = True
            # more checks to come, just doing basic for now.

            try:
                submitted_core_label = request.args.get('core_label')[0]
                webinterface._Configs.set('core', 'label', submitted_core_label)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Label.")

            try:
                submitted_master_gateway = request.args.get('master_gateway')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Master gateway not selected.")
            try:
                gateway = webinterface._Gateways[submitted_master_gateway]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid master gateway selection, selection doesn't exist.")

            try:
                submitted_core_description = request.args.get('core_description')[0]
                webinterface._Configs.set('core', 'description', submitted_core_description)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Description.")


            if valid_submit:
                try:
                    if submitted_master_gateway == webinterface.gateway_id():
                        is_master = True
                    else:
                        is_master = False
                    data = {
                        'label': submitted_core_label,
                        'description': submitted_core_description,
                        'master_gateway': submitted_master_gateway,
                        'is_master': is_master,
                    }
                    # print("data: %s" % data)
                    results = yield webinterface._YomboAPI.request('PATCH',
                                                                   '/v1/gateway/%s' % webinterface.gateway_id(),
                                                                   data,
                                                                   session=session['yomboapi_session'])
                    # print("api results: %s" % results)

                    previous_master_gateway = webinterface._Configs.get('core', 'master_gateway', None, False)
                    if previous_master_gateway != submitted_master_gateway:
                        webinterface._Configs.set('core', 'is_master', is_master)
                        webinterface._Configs.set('core', 'master_gateway', submitted_master_gateway)
                        webinterface._Notifications.add({'title': 'Restart Required',
                                                         'message': 'A critical configuration change has occured and requires a restart: The master gateway has been changed.',
                                                         'source': 'Web Interface',
                                                         'persist': False,
                                                         'priority': 'high',
                                                         'always_show': True,
                                                         'always_show_allow_clear': False,
                                                         'id': 'reboot_required',
                                                         'local': True,
                                                         })

                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/configs/basic')

            try:
                submitted_location_searchtext = request.args.get('location_searchtext')[0]
                webinterface._Configs.set('location', 'searchbox', submitted_location_searchtext)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Location Search Entry.")

            try:
                submitted_location_latitude = request.args.get('location_latitude')[0]
                webinterface._Configs.set('location', 'latitude', submitted_location_latitude)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Lattitude.")

            try:
                submitted_location_longitude = request.args.get('location_longitude')[0]
                webinterface._Configs.set('location', 'longitude', submitted_location_longitude)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Longitude.")

            try:
                submitted_location_elevation = request.args.get('location_elevation')[0]
                webinterface._Configs.set('location', 'elevation', submitted_location_elevation)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Elevation.")

            try:
                submitted_webinterface_enabled = request.args.get('webinterface_enabled')[0]
                webinterface._Configs.set('webinterface', 'enabled', submitted_webinterface_enabled)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Enabled/Disabled value.")

            try:
                submitted_webinterface_localhost_only = request.args.get('webinterface_localhost_only')[0]
                webinterface._Configs.set('webinterface', 'localhost_only', submitted_webinterface_localhost_only)
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Localhost Only Selection.")

            try:
                new_port = int(request.args.get('webinterface_nonsecure_port')[0])
                if new_port == 0:
                    submitted_webinterface_nonsecure_port = new_port
                    webinterface._Configs.set('webinterface', 'nonsecure_port', submitted_webinterface_nonsecure_port)
                elif new_port == webinterface._Configs.get('webinterface', 'nonsecure_port'):
                    submitted_webinterface_nonsecure_port = new_port
                    webinterface._Configs.set('webinterface', 'nonsecure_port', submitted_webinterface_nonsecure_port)
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.bind(("127.0.0.1", new_port))
                    except socket.error as e:
                        if e.errno == 98:
                            webinterface.add_alert("Invalid webinterface non_secure port, appears to be in use already.")
                        else:
                            # something else raised the socket.error exception
                            webinterface.add_alert("Invalid webinterface non_secure port, unable to access: %s" % e)
                        valid_submit = False
                    else:
                        webinterface._Configs.set('webinterface', 'nonsecure_port', new_port)
            except Exception as e:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface non_secure port: %s" % e)

            try:
                new_port = int(request.args.get('webinterface_secure_port')[0])
                if new_port == 0:
                    webinterface._Configs.set('webinterface', 'secure_port', new_port)
                elif new_port == new_port:
                    webinterface._Configs.set('webinterface', 'secure_port', new_port)
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.bind(("127.0.0.1", new_port))
                    except socket.error as e:
                        if e.errno == 98:
                            webinterface.add_alert("Invalid webinterface secure port, appears to be in use already.")
                        else:
                            # something else raised the socket.error exception
                            webinterface.add_alert("Invalid webinterface secure port, unable to access: %s" % e)
                        valid_submit = False
                    else:
                        webinterface._Configs.set('webinterface', 'secure_port', new_port)
            except Exception as e:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface secure port: %s" % e)

            try:
                submitted_webinterface_pin_type=request.args.get('webinterface_pin_type')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid web interface auth pin type.")
            else:
                if submitted_webinterface_pin_type == "pin":
                    try:
                        submitted_webinterface_auth_pin = request.args.get('webinterface_auth_pin')[0]
                    except:
                        webinterface.add_alert("No auth access code set, required when auth type set to 'access code'.")
                        valid_submit = False
                    else:
                        webinterface._Configs.set('webinterface', 'auth_pin_type', submitted_webinterface_pin_type)
                        webinterface._Configs.set('webinterface', 'auth_pin', submitted_webinterface_auth_pin)
                elif submitted_webinterface_pin_type == "totp":
                        webinterface._Configs.set('webinterface', 'auth_pin_type', submitted_webinterface_pin_type)
                elif submitted_webinterface_pin_type == "none":
                        webinterface.add_alert("No auth type set. This is unwise.")
                        webinterface._Configs.set('webinterface', 'auth_pin_type', submitted_webinterface_pin_type)

            try:
                webinterface._Configs.set('localization', 'degrees', request.args.get('localization_degrees')[0])
            except:
                print("can't save degrees")
                pass

            configs = webinterface._Configs.get("*", "*")

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/dns', methods=['GET'])
        @require_auth()
        def page_configs_dns_get(webinterface, request, session):
            configs = webinterface._Configs.get("*", "*")

            dns_configs = webinterface._Configs.get("dns", "*")
            if dns_configs is None:
                dns_configs = {
                    'dns_name': 'None',
                    'dns_domain': 'None',
                    'dns_domain_id': 'None',
                    'allow_change_at': int(time()),
                    'fqdn': 'None',
                }

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/dns.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/configs/dns", "DNS")

            return page.render(alerts=webinterface.get_alerts(),
                               dns_configs=dns_configs,
                               )

        @webapp.route('/dns', methods=['POST'])
        @require_auth(login_redirect="/configs/basic")
        @inlineCallbacks
        def page_configs_dns_post(webinterface, request, session):

            try:
                submitted_dns_name = request.args.get('dns_name')[0]  # underscore here due to jquery
            except:
                webinterface.add_alert("Select a valid dns name.")
                return  webinterface.redirect(request, '/configs/dns')

            try:
                submitted_dns_domain = request.args.get('dns_domain_id')[0]  # underscore here due to jquery
            except:
                webinterface.add_alert("Select a valid dns domain.")
                return  webinterface.redirect(request, '/configs/dns')

            data = {
                'dns_name': submitted_dns_name,
                'dns_domain_id': submitted_dns_domain,
            }

            try:
                dns_results = yield webinterface._YomboAPI.request('POST',
                                                                   '/v1/gateway/%s/dns_name' % webinterface.gateway_id(),
                                                                   data,
                                                                   session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/configs/dns')

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'DNS Changed. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             'local': True,
                                             })

            webinterface._Configs.set('dns', 'dns_name', dns_results['data']['dns_name'])
            webinterface._Configs.set('dns', 'dns_domain', dns_results['data']['dns_domain'])
            webinterface._Configs.set('dns', 'dns_domain_id', dns_results['data']['dns_domain_id'])
            webinterface._Configs.set('dns', 'allow_change_at', dns_results['data']['allow_change_at'])
            webinterface._Configs.set('dns', 'fqdn', dns_results['data']['fqdn'])

            dns_configs = webinterface._Configs.get("dns", "*")
            if dns_configs is None:
                dns_configs = {
                    'dns_name': 'None',
                    'dns_domain': 'None',
                    'dns_domain_id': 'None',
                    'allow_change_at': int(time()),
                    'fqdn': 'None',
                }

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/dns.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/configs/dns", "DNS")
            return page.render(alerts=webinterface.get_alerts(),
                               dns_configs=dns_configs,
                               )

        @webapp.route('/yombo_ini')
        @require_auth(login_redirect="/configs/yombo_ini")
        def page_configs_yombo_ini(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/yombo_ini.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/configs/basic", "Yombo.ini")
            return page.render(alerts=webinterface.get_alerts(),
                               configs=webinterface._Libraries['configuration'].configs
                               )

        @webapp.route('/gpg/index')
        @require_auth(login_redirect="/configs/gpg/index")
        @inlineCallbacks
        def page_gpg_keys_index(webinterface, request, session):
            db_keys = yield webinterface._LocalDB.get_gpg_key()
            gw_fingerprint = webinterface._Configs.get('gpg', 'fingerprint')
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/gpg/index", "GPG Keys")
            return page.render(
                alerts=webinterface.get_alerts(),
                gpg_keys=db_keys,
                gw_fingerprint=gw_fingerprint,
            )

        @webapp.route('/gpg/generate_key')
        @require_auth(login_redirect="/configs/gpg/generate_key")
        def page_gpg_keys_generate_key(webinterface, request, session):
            request_id = random_string(length=16)
    #        self._Libraries['gpg'].generate_key(request_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_generate_key_started.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/gpg/index", "GPG Keys")
            webinterface.add_breadcrumb(request, "/gpg/generate_key", "Generate Key")
            return page.render(request_id=request_id, getattr=getattr, type=type)

        @webapp.route('/gpg/genrate_key_status')
        @require_auth(login_redirect="/configs/genrate_key_status")
        def page_gpg_keys_generate_key_status(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_generate_key_status.html')
            return page.render(atoms=webinterface._Libraries['atoms'].get_atoms(),
                               getattr=getattr,
                               type=type)
