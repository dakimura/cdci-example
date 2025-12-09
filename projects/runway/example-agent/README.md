

# Example Agent for Runway


## setup

initialize your project
```zsh
uv init
```

get your Application Default Credentials
```
gcloud auth login --update-adc```
```

initialize a runway service
```
runway init \
--service-name=example-agent \
--gcp_project=akkie-dev \
--ci=githubactions
```
