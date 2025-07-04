FROM minizinc/minizinc:latest

WORKDIR ./cdmo

COPY . .

RUN apt-get update \
 && apt-get install -y python3 \
 && apt-get install -y python3-pip
 # && python3 -m pip install -r requirements.txt 

CMD ["/bin/bash"]