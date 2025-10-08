RULES = {
    "javascript": {
        "files": ["package.json"],
        "pkgs": {
            "express":"Express","next":"Next.js","nestjs":"NestJS","nuxt":"Nuxt",
            "angular":"Angular","@angular/core":"Angular","sveltekit":"SvelteKit",
            "koa":"Koa","hapi":"hapi","remix":"Remix","fastify":"Fastify"
        }
    },
    "python": {
        "files": ["pyproject.toml","requirements.txt"],
        "pkgs": {"django":"Django","flask":"Flask","fastapi":"FastAPI","starlette":"Starlette","tornado":"Tornado"}
    },
    "java": {
        "files": ["pom.xml","build.gradle","build.gradle.kts"],
        "markers": {"spring-boot-starter":"Spring Boot","spring-framework":"Spring","quarkus-":"Quarkus","io.micronaut":"Micronaut"}
    },
    "ruby": {"files": ["Gemfile"], "pkgs": {"rails":"Rails","sinatra":"Sinatra"}},
    "php": {"files": ["composer.json"], "pkgs": {"laravel/framework":"Laravel","symfony/framework-bundle":"Symfony","codeigniter4/framework":"CodeIgniter"}},
    "go": {"files": ["go.mod"], "markers": {"github.com/gin-gonic/gin":"Gin","github.com/labstack/echo":"Echo","github.com/gofiber/fiber":"Fiber"}},
    "rust": {"files": ["Cargo.toml"], "pkgs": {"actix-web":"Actix","rocket":"Rocket","axum":"Axum"}}
}
TARGET_FILENAMES = {
    "package.json","pyproject.toml","requirements.txt",
    "pom.xml","build.gradle","build.gradle.kts",
    "Gemfile","composer.json","go.mod","Cargo.toml"
}