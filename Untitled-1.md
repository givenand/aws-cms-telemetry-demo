
A few commands that I use when setting the environment up on a Cloud9 instance:

```bash
pip install virtualenv
brew install pyenv-virtualenv

vim ~/.zshrc

# Setup virtualenv home
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Tell pyenv-virtualenvwrapper to use pyenv when creating new Python environments
export PYENV_VIRTUALENVWRAPPER_PREFER_PYVENV="true"

# Set the pyenv shims to initialize
if command -v pyenv 1>/dev/null 2>&1; then
 eval "$(pyenv init -)"
fi

mkdir ~/.virtualenvs

pyenv global 3.6.12

pyenv virtualenv 3.6.12 CMS

pip install nvm

nvm install 12.18.2

nvm use 12.18.2 

npm install -g pnpm@3.5.3

brew install --cask docker
````