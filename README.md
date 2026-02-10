# CSE 4504 Team Project

## GitHub Workflow
During the development of this project, the following workflow will be used for each stage (feature). The diagram shows the workflow for feature_1. For each subsequent feature, the same workflow will be used (replacing feature_1 with a different feature number or name).
```mermaid
flowchart TD
    Start([Start Project]) --> InitFeature[Create 'feature_1' branch from main]
    subgraph Team_Start [Team Design Work]
    InitFeature --> Design[Design interfaces, commit and push to 'feature_1']
    Design --> DivideTasks[Divide implementation work among teammates. Update README.md file with Work Assignment section, specifying individual implementation responsibilities.]
    end

    subgraph Indiv_Work [Individual Development Work]
    DivideTasks --> BranchInd[Create individual task branch]
    BranchInd --> Implement[Implement assigned components]
    Implement --> PR_Ind[Open PR from individual task branch to 'feature_1']
    end
    style Indiv_Work fill:#96C9F2

    subgraph Team Integration Work
    Review_Ind -- Changes Needed --> Implement
    PR_Ind --> Review_Ind{Team Review}
    Review_Ind -- Approved --> Merge_Ind[Merge to 'feature_1']    
    Merge_Ind --> Pull[Pull updated 'feature_1']
    Pull --> Test[Run integration tests]
    Test --> Fix{Bugs Found?}
    Fix -- Yes --> FixCommit[Commit fixes to 'feature_1']
    FixCommit --> Test
    Fix -- No --> FinalPR[Open PR from feature_1 to 'main']
    FinalPR --> Review_Final{Final Review}
    Review_Final -- Approved --> MainMerge[Merge to 'main']
    end

    MainMerge --> Done([Feature Complete])
```
## Work Assignments

Cliff - Runner Object - 
Lesly - Workout Object
Joel - csvInput within aplication layer

Workout and Runner connecton in Aplication Dir and Workout Config