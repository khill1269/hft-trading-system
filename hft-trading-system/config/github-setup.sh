#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up GitHub repository...${NC}"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Please install git first.${NC}"
    exit 1
fi

# Get GitHub username and repo name
read -p "Enter your GitHub username: " github_username
read -p "Enter repository name [hft_trading_system]: " repo_name
repo_name=${repo_name:-hft_trading_system}

# Check if repository already exists
echo -e "${GREEN}Checking if repository exists...${NC}"
repo_check=$(curl -s -o /dev/null -w "%{http_code}" https://github.com/$github_username/$repo_name)

if [ $repo_check -eq 200 ]; then
    read -p "Repository already exists. Do you want to proceed? [y/N]: " proceed
    if [[ $proceed != "y" && $proceed != "Y" ]]; then
        echo -e "${RED}Aborting.${NC}"
        exit 1
    fi
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo -e "${GREEN}Initializing git repository...${NC}"
    git init
fi

# Create GitHub repository using GitHub CLI if available
if command -v gh &> /dev/null; then
    echo -e "${GREEN}Creating GitHub repository using GitHub CLI...${NC}"
    gh repo create $repo_name --private --confirm
else
    echo -e "${BLUE}Please create a repository manually on GitHub: https://github.com/new${NC}"
    read -p "Press enter when ready..."
fi

# Configure git
echo -e "${GREEN}Configuring git...${NC}"
read -p "Enter your Git email: " git_email
read -p "Enter your Git name: " git_name

git config user.email "$git_email"
git config user.name "$git_name"

# Add GitHub remote
echo -e "${GREEN}Adding GitHub remote...${NC}"
git remote add origin https://github.com/$github_username/$repo_name.git

# Create main branch
echo -e "${GREEN}Creating main branch...${NC}"
git checkout -b main

# Stage all files
echo -e "${GREEN}Staging files...${NC}"
git add .

# Commit
echo -e "${GREEN}Committing files...${NC}"
git commit -m "Initial commit"

# Push to GitHub
echo -e "${GREEN}Pushing to GitHub...${NC}"
git push -u origin main

echo -e "${BLUE}GitHub setup complete!${NC}"
echo -e "${GREEN}Next steps:${NC}"
echo "1. Visit https://github.com/$github_username/$repo_name to view your repository"
echo "2. Set up branch protection rules"
echo "3. Configure GitHub Actions"
echo "4. Set up project settings and collaborators"
