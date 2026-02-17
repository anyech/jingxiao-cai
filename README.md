# Jingxiao Cai - Personal Website

Personal portfolio website hosted on GitHub Pages.

## Development

To preview locally:
```bash
# Option 1: Simple HTTP server
python3 -m http.server 8000

# Option 2: Using npm serve
npx serve .
```

Then open http://localhost:8000

## Deployment

This site is automatically deployed via GitHub Pages from the `main` branch.

To update:
1. Edit `index.html`
2. Commit and push:
```bash
git add .
git commit -m "Update website"
git push origin main
```

GitHub Pages will automatically deploy changes.

## Custom Domain (Optional)

To use a custom domain:
1. Go to repo Settings → Pages
2. Add your custom domain under "Custom domain"
3. Create appropriate DNS records

## License

MIT