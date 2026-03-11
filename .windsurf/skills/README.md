# Ralph Wiggum Skills

Skills provide structured, multi-step automation for the Ralph Wiggum Methodology.

## Available Skills

### ralph-initialize
**Purpose:** Initialize a new project with Ralph methodology
**When to use:** Starting a new project or setting up Ralph for the first time
**What it does:**
- Creates `prd.json` backlog file
- Creates `progress.md` tracking log
- Sets up `.windsurf/rules/tech-stack.md` with your tech stack
- Generates initial task backlog (typically 5-15 tasks)

### ralph-cycle
**Purpose:** Execute a single development cycle
**When to use:** Ready to implement the next feature from the backlog
**What it does:**
- Selects highest-priority failing task
- Plans implementation approach
- Implements the feature
- Runs verification tests
- Commits on success

### ralph-deep-init
**Purpose:** Build comprehensive backlog through architectural analysis
**When to use:** Complex projects needing large, well-organized backlogs (20-40+ tasks)
**What it does:**
- Identifies 6 functional architectural groups
- Generates 3-5 tasks per group
- Creates comprehensive `prd.json`
- Organizes tasks by technical domain

## How Skills Work

### Automatic Invocation
Cascade automatically invokes skills when your request matches the skill description:
- "I need to set up Ralph for my Node.js API project" → invokes ralph-initialize
- "Implement the next task from the backlog" → invokes ralph-cycle
- "Create a large backlog for my e-commerce platform" → invokes ralph-deep-init

### Manual Invocation
Use `@skill-name` to explicitly invoke a skill:
```
@ralph-cycle please implement the authentication task
```

### Progressive Disclosure
Skills use progressive disclosure - Cascade reads the SKILL.md file first, then accesses supporting resources only when needed.

## Supporting Resources

Each skill includes reference files:

**ralph-initialize:**
- `prd-template.json` - Product requirements structure
- `progress-template.md` - Progress log format
- `tech-stack-template.md` - Tech stack documentation

**ralph-cycle:**
- `cycle-checklist.md` - Quick reference for each cycle
- `verification-examples.md` - Test commands for various tech stacks

**ralph-deep-init:**
- `architecture-examples.md` - Sample functional group breakdowns
- `task-examples.json` - Well-formed task examples
- `groups-template.json` - Template for architecture groups

## Ralph Methodology Quick Reference

### Core Files
- `prd.json` - Product Requirements Document (backlog)
- `progress.md` - Development log
- `.windsurf/rules/tech-stack.md` - Tech stack and conventions

### Workflow
1. **Initialize:** Use `@ralph-initialize` or `@ralph-deep-init`
2. **Cycle:** Repeatedly use `@ralph-cycle` to implement tasks
3. **Track:** All work is logged in `progress.md`
4. **Verify:** Every task must pass tests before marking complete

### Constraints
- One task at a time
- Tests must pass before commit
- All work logged to `progress.md`
- `prd.json` is the source of truth
