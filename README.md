## Setup

- Dependencies:
  - Install `pdm`
  - Use `pdm sync` to create a virtual env with the rest

- Create a `local` folder in the repo root, with the following contents.

  - `local/state/`: empty dir

  - `local/config.json`:

    ```json
    {
        "chat_id": null,
        "recordings_dir": "<your_path>"
    }
    ```

  - `local/secrets.json`:

    ```json
    {
        "api_token": "<your_token>"
    }
    ```

- Get the chat ID:
  - Write a message to the bot
  - Execute `pdm run run_bot`. It will print the ID (and some more info).
  - Edit `local/config.json`; format the ID as an integer.

- Run the command regularly: `pdm run run_bot`