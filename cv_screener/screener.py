"""Pipeline orchestration - ties every module together.

OWNER: Ojeaga Jeffrey  (System Integration, Exception Handling & Testing)

The "spine" of the app: the GUI calls this, which runs the full pipeline -
read CVs -> regex match -> AI analyse -> rank -> classify -> organize - and
returns a ranked list of results. Adds the exception handling around each step.
"""
