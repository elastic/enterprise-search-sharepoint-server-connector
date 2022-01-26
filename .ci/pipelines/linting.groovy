//
// Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
// or more contributor license agreements. Licensed under the Elastic License 2.0;
// you may not use this file except in compliance with the Elastic License 2.0.
//

// Loading the shared lib
@Library(['estc', 'entsearch']) _

eshPipeline(
    timeout: 45,
    project_name: 'Enterprise Search Sharepoint Server 2016 Connector',
    repository: 'enterprise-search-sharepoint-server-2016-connector',
    stage_name: 'Linting',
    stages: [
        [
            name: 'Make Lint',
            type: 'script',
            label: 'Makefile',
            script: {
                withMaven {
                    sh 'make lint'
                }
            },
            match_on_all_branches: true,
        ]
    ]
)
