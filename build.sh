#/bin/env bash
ROOT=$(pwd)
echo "\tУСТАНОВКА ЗАВИСИМОСТЕЙ"
echo "Команда: poetry install"
poetry install
echo "\tУСТАНОВКА ЗАВИСИМОСТЕЙ ЗАВЕРШЕНА"
echo "\n\n\n"

echo "\tСБОРКА ПРОЕКТА"
echo "Команда: poetry build"
poetry build
echo "\tСБОРКА ПРОЕКТА ЗАВЕРШЕНА"
echo "В папке dist расположены дистрибутивы sdist и wheel"
echo "\n\n\n"

echo "\tСБОРКА ДОКУМЕНТАЦИИ"
echo "Команда: cd docs && make html"
cd docs && make html
cd $ROOT
echo "\tСБОРКА ДОКУМЕНТАЦИИ ЗАВЕРШЕНА"
echo "Документация расположена в папке: docs/build/html"
echo "\n\n\n"

echo "\tСБОРКА DOCKER-ОБРАЗА"
if [ -f /usr/bin/docker ]
then
    docker build -t python_runner_bot .
else
    echo "Файл /usr/bin/docker не обнаружен в системе. Помните, что для работы бота также требуется установленный в системе Docker Engine"
fi


