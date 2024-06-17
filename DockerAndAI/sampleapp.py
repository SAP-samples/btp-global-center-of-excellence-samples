
from os import environ as osenv
from subprocess import run as subrun

html_env="<ul>" + "\n".join([f"<li>{k}:  {v}</li>" for k,v in osenv.items()]) + "</ul>"
cp=subrun(['python3', '-m', 'pip', 'list', '--no-color'], capture_output=True)
html_pip="<ul>" + "\n".join([ f"<li>{l.split()[0]}:  {l.split()[1]}</li>" for l in cp.stdout.decode().split('\n')[2:-1]]) + "</ul>"

def app(query, start_response):
        elements=set(list(query.keys()))

        html_query="<ul>" + "\n".join(
                [ f"<li>{k}:  {query[k]}</li>" 
                    for k in sorted(elements) ]) + "</ul>"
        html_data=f"""<html>
            <p>http request{html_query}</p>
            <p>pip modules{html_pip}</p>
            <p>environment variables {html_env}</p>
        </html>"""
        data = html_data.encode()
        start_response("200 OK", [
            ("Content-Type", "text/html"),
            ("Content-Length", str(len(data)))
        ])
        return iter([data])

