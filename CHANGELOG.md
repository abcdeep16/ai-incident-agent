# Changelog

This changelog summarizes significant changes that can be verified from the
current Git history and working tree. It is not a claim that every historical
change is listed.

## Unreleased — current working tree

- Replaced the current incident-analysis path with local anomaly-model
  inference, heuristic training, and saved model artifacts, as verified in
  `ai-service/main.py`, `services/llm_service.py`,
  `services/local_model_service.py`, and `train_local_model.py`.
- Added a default backend API URL in the frontend so local development works
  when `VITE_API_URL` is unset.
- Allowed both `localhost` and `127.0.0.1` local Vite origins in backend CORS.
- Added the AI-focused project documentation set.
- These changes were present as working-tree changes when this entry was
  written; they were not all represented by the checked-out Git commit.

## 2026-09-06

- Added the comprehensive README (`dba1968`).
- Git history records Gemini model selection/fallback and overload retry work
  (`5b36b48`, `113bfff`, `ee60598`); that historical implementation is not the
  current local-classifier path.
- Added support for `HEAD /health` (`985d738`).
- Replaced the project with a corrected full-stack version (`a18d1d4`).

## 2026-08-20 to 2026-08-22

- Added a structured incident investigation pipeline and evidence-grounded
  analysis (`ca87ae5`, `54c5077`, `46a9e57`).
- Updated the incident UI and backend (`80ea26e`).
- Added deployment preparation, lazy embedding-model loading, and Python
  dependency fixes (`2f6df8e`, `1fcd43f`, `d659411`, `9377bfb`,
  `994cbac`).
- Expanded allowed CORS origins for deployment (`97caaaa`, `aa55dcf`).

Commit identifiers refer to this repository's Git history at documentation
creation time. Consult `git log` for complete commit-level details.
