REPO_LIST_Q = """
query($login:String!, $after:String){
  repositoryOwner(login:$login){
    repositories(first:100, after:$after, orderBy:{field:NAME, direction:ASC}){
      pageInfo{ hasNextPage endCursor }
      nodes{ name owner{login} }
    }
  }
}
"""

REPO_SUMMARY_Q = """
query($owner:String!, $name:String!){
  repository(owner:$owner, name:$name){
    name
    url
    isArchived
    defaultBranchRef{ name }
    languages(first:20, orderBy:{field:SIZE, direction:DESC}){
      edges{ size node{ name } }
    }
  }
}
"""

HEAD_Q = """
query($owner:String!, $name:String!){
  repository(owner:$owner, name:$name){
    defaultBranchRef{
      name
      target{ ... on Commit { oid } }
    }
  }
}
"""

BLOB_Q = """
query($owner:String!, $name:String!, $expr:String!){
  repository(owner:$owner, name:$name){
    object(expression:$expr){ ... on Blob { text byteSize isBinary } }
  }
}
"""

CONTRIB_HISTORY_Q = """
query($owner:String!, $name:String!, $after:String){
  repository(owner:$owner, name:$name){
    defaultBranchRef{
      target{
        ... on Commit{
          history(first:100, after:$after){
            pageInfo{ hasNextPage endCursor }
            nodes{ author{ user{ login } email name } }
          }
        }
      }
    }
  }
}
"""