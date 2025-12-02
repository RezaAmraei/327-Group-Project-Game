I started out running these commands to start this:

    brew install rabbitmq
    echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
    brew services start rabbitmq
    rabbitmq-plugins enable rabbitmq_management

verify its working:
    brew services list | grep rabbitmq

open the ui:
#login creditentials: guest / guest
    open http://localhost:15672     

FOR GROUP MATES
STEP 1 SETUP:
for groupmates(on apple devices):
    brew install rabbitmq
    echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
    brew services start rabbitmq
    rabbitmq-plugins enable rabbitmq_management

on windows(i didnt test this on windows so not sure if this 100% works):
Install Erlang, then RabbitMQ (MSI).
Open “RabbitMQ Command Prompt (sbin)”:
in bat terminal:
    rabbitmq-plugins.bat enable rabbitmq_management 
    net start RabbitMQ
then verify it works Verify the UI: 
    open http://localhost:15672 #(login: guest / guest).

STEP 2 IMPORT DEFINITONS(import/export definitons may not be there in your ui, there will be an alternate step if you run into this problem like i did):
    1. Go to http://localhost:15672
        1a. go to admin tab
    2. I NEED TO GIVE YOU THE JSON FILE FOR YOU TO DO THIS STEP
    2. Scroll to Import / export definitions → Choose file → select game-events-defs.json
    3. click import

STEP 2 ALTERNATIVE- import through the terminal
    macOS / Linux:
        # from the folder where the JSON lives
        # replace the filename if needed
        curl -u guest:guest \
            -H "content-type: application/json" \
            -X POST \
            -d @game-events-defs.json \
            http://localhost:15672/api/definitions
    windows(powershell):
        # from the folder where the JSON lives
        $pair = "guest:guest"
        $basicAuth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
        Invoke-RestMethod -Method Post `
            -Uri "http://localhost:15672/api/definitions" `
            -Headers @{ "Authorization" = "Basic $basicAuth"; "content-type" = "application/json" } `
            -InFile "game-events-defs.json"


STEP 3 VERIFY THIS ALL WORKED:

Verify (no code required) go to these tabs and if you see this info youre good
	•	Exchanges → confirm game.events (type: topic, durable) exists.
	•	Queues → confirm notify-gateway and leaderboard-worker exist.
	•	Bindings:
	•	notify-gateway should have match.* and player.*.result from game.events.
	•	leaderboard-worker should have match.ended from game.events.

Quick smoke test:
	1.	Exchanges → game.events → Publish message
	•	Routing key: match.ready
	•	Payload: { "ok": true } → Publish
	2.	Queues → notify-gateway → Get messages → Get Message(s) → you should see it.
	3.	Publish with Routing key match.ended → check leaderboard-worker.
    