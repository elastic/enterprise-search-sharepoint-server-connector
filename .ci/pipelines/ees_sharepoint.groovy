---

- job:
    name: ees_sharepoint/linters
    description: "Runs flake8 linter against the enterprise-search-sharepoint-server-2016-connector repository"
    project-type: multibranch
    node: master
    concurrent: true
    script-path: .ci/pipelines/ees_sharepoint.groovy
    prune-dead-branches: true
    scm:
      - github:
          repo: enterprise-search-sharepoint-server-2016-connector
          repo-owner: elastic
          reference-repo: /var/lib/jenkins/.git-references/enterprise-search-sharepoint-server-2016-connector.git
          disable-pr-notifications: true
          branch-discovery: all
          discover-pr-origin: current
          discover-pr-forks-strategy: false
          discover-pr-forks-trust: nobody
          discover-tags: false
          build-strategies:
            - regular-branches: true
          property-strategies:
            all-branches:
              - pipeline-branch-durability-override: performance-optimized
          credentials-id: 2a9602aa-ab9f-4e52-baf3-b71ca88469c7-UserAndToken
          ssh-checkout:
            credentials: f6c7695a-671e-4f4f-a331-acdce44ff9ba
          clean:
            after: true
            before: true
          prune: true
          timeout: 10
