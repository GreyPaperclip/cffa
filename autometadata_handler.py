import json, urllib
import ssl
import urllib.request
import urllib.parse

def addUserIDtoUser(session, domainURI, auth0clientID, auth0clientSecret, auth0Audience, userID):
    try:
        # first get token
        ctx = ssl.create_default_context()
        ctx.load_default_certs()

        base_url = "https://{domain}".format(domain=domainURI)
        data = urllib.parse.urlencode([('client_id', auth0clientID),
                                 ('client_secret', auth0clientSecret),
                                 ('audience', auth0Audience),
                                 ('grant_type', "client_credentials")])
        req = urllib.request.Request(base_url + "/oauth/token", data.encode('utf-8'))
        response = urllib.request.urlopen(req, context=ctx)
        oauth = json.loads(response.read())
        access_token = oauth['access_token']

        # now set up request to send metadata
        req = urllib.request.Request(base_url + "api/v2/users/" + session.get('user_id'))
        req.add_header('Authorization', 'Bearer ' + access_token)
        req.add_header('Content-Type', 'application/json')
        req.get_method = lambda: 'PATCH'

        data = urllib.request.Request([('app_metadata', ('userID', userID))])

        try:
            response = urllib.request.Request(req, data)
            res = json.loads(response.read())
        except urllib.request.HTTPError as e:
            print('HTTPError = ' + str(e.code) + ' ' + str(e.reason))
        except urllib.URLError as e:
            print('URLError = ' + str(e.reason))
        except urllib.HTTPException as e:
            print('HTTPException')
        except Exception:
            print('Generic Exception')
    except Exception as e:
        print("Updating metadata at Auth0 failed ")

    return(True)


